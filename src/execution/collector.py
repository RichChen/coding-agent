"""Bounded concurrent stdout/stderr collectors (no full communicate-then-truncate)."""

from __future__ import annotations

import asyncio
from pathlib import Path

from src.execution.base import (
    OutputQuotas,
    RunOutputMeter,
    StreamCapture,
    ToolArtifactBudget,
)


async def collect_stream(
    stream: asyncio.StreamReader | None,
    *,
    quotas: OutputQuotas,
    run_meter: RunOutputMeter | None,
    artifact_path: Path | None,
    artifact_budget: ToolArtifactBudget | None = None,
    cancel_producer: asyncio.Event | None = None,
) -> StreamCapture:
    """Read stream in chunks; cap per-stream memory and shared per-tool artifact."""
    cap = StreamCapture()
    if stream is None:
        return cap

    memory_buf = bytearray()
    artifact_file = None

    try:
        if artifact_path is not None:
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_file = open(artifact_path, "wb")

        while True:
            if cancel_producer is not None and cancel_producer.is_set():
                break
            if run_meter is not None and run_meter.producers_stopped:
                break
            try:
                # Bounded read wait so cancel_producer can be observed without EOF hang.
                try:
                    chunk = await asyncio.wait_for(stream.read(8192), timeout=0.1)
                except asyncio.TimeoutError:
                    continue
            except (BrokenPipeError, ConnectionResetError):
                break
            except asyncio.CancelledError:
                raise
            if not chunk:
                break

            cap.read_chunks += 1
            cap.bytes_seen += len(chunk)
            if run_meter is not None:
                run_meter.note_read(len(chunk), len(memory_buf) + len(chunk))

            room_mem = quotas.memory_per_stream_bytes - len(memory_buf)
            if room_mem > 0:
                take = min(room_mem, len(chunk))
                memory_buf.extend(chunk[:take])
                cap.bytes_kept_memory += take
                if take < len(chunk):
                    cap.truncated = True
            else:
                cap.truncated = True

            if len(memory_buf) > cap.peak_buffer_bytes:
                cap.peak_buffer_bytes = len(memory_buf)

            writable = chunk
            if run_meter is not None:
                allow = run_meter.try_keep(len(writable))
                if allow < len(writable):
                    writable = writable[:allow]
                    cap.truncated = True
                    if cancel_producer is not None:
                        cancel_producer.set()
                    if allow == 0:
                        break

            if artifact_file is not None and writable:
                budget = artifact_budget
                if budget is None:
                    # Fallback: local-only (should not happen when wired correctly)
                    art_take = min(len(writable), quotas.artifact_per_tool_bytes - cap.bytes_kept_artifact)
                else:
                    art_take = budget.take(len(writable))
                if art_take <= 0:
                    cap.truncated = True
                else:
                    artifact_file.write(writable[:art_take])
                    cap.bytes_kept_artifact += art_take
                    if art_take < len(writable):
                        cap.truncated = True

            if run_meter is not None and run_meter.cancelled_producer:
                if cancel_producer is not None:
                    cancel_producer.set()
                break

        cap.text_preview = bytes(memory_buf).decode("utf-8", errors="replace")
        if artifact_file is not None:
            cap.artifact_path = str(artifact_path)
    finally:
        if artifact_file is not None:
            try:
                artifact_file.close()
            except OSError:
                pass

    return cap
