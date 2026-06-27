"""run_command：在 workspace 目录下执行 shell 或 argv，并走 CommandPolicy。

English: subprocess shell/argv in workspace cwd with policy gate + timeout + env whitelist.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import time

from src.tools.base import Tool, ToolContext, ToolResult

_SYSTEM_ENV_KEYS = frozenset(
    {"PATH", "SYSTEMROOT", "SystemRoot", "HOME", "USERPROFILE", "TEMP", "TMP", "COMSPEC", "WINDIR"}
)


class RunCommandTool(Tool):
    name = "run_command"
    description = (
        "Execute a command inside the workspace directory. "
        "Provide either `command` (shell string) or `argv` (argument array for non-shell exec)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "Shell command string (mutually exclusive with argv).",
            },
            "argv": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Argv list for non-shell execution (mutually exclusive with command).",
            },
        },
    }

    def __init__(
        self,
        command_policy=None,
        timeout_seconds: int = 30,
        env_whitelist: list[str] | None = None,
        prefer_argv: bool = False,
    ):
        self.command_policy = command_policy
        self.timeout_seconds = timeout_seconds
        self.env_whitelist = env_whitelist or []
        self.prefer_argv = prefer_argv

    @staticmethod
    def _build_subprocess_env(env_whitelist: list[str]) -> dict[str, str] | None:
        if not env_whitelist:
            return None
        allowed = {key.upper() for key in env_whitelist} | {k.upper() for k in _SYSTEM_ENV_KEYS}
        return {
            key: value
            for key, value in os.environ.items()
            if key.upper() in allowed
        }

    @staticmethod
    def _append_execution_meta(
        combined: str,
        *,
        exit_code: int | None,
        duration_ms: float,
        timed_out: bool,
    ) -> str:
        code = "null" if exit_code is None else str(exit_code)
        return (
            f"{combined}\n"
            f"[exit_code={code} duration_ms={duration_ms:.0f} timed_out={str(timed_out).lower()}]"
        )

    def _emit_command_event(
        self,
        ctx: ToolContext,
        *,
        mode: str,
        exit_code: int | None,
        duration_ms: float,
        timed_out: bool,
        success: bool,
    ) -> None:
        event_bus = ctx.extra.get("event_bus")
        if not event_bus:
            return
        event_bus.emit(
            "command_executed",
            mode=mode,
            exit_code=exit_code,
            duration_ms=round(duration_ms, 2),
            timed_out=timed_out,
            success=success,
        )

    async def execute(self, params: dict, ctx: ToolContext) -> ToolResult:
        call_id = params.get("_call_id", "")
        command = str(params.get("command", "")).strip()
        argv = params.get("argv")
        use_argv = isinstance(argv, list) and len(argv) > 0

        if use_argv and command:
            return ToolResult(
                call_id=call_id,
                name=self.name,
                success=False,
                output="",
                error="Provide either command or argv, not both.",
            )
        if not use_argv and not command:
            return ToolResult(
                call_id=call_id,
                name=self.name,
                success=False,
                output="",
                error="No command or argv provided.",
            )

        env = self._build_subprocess_env(self.env_whitelist)
        start = time.monotonic()
        timed_out = False
        exit_code: int | None = None
        mode = "argv" if use_argv else "shell"

        if use_argv:
            argv = [str(part) for part in argv]
            if self.command_policy:
                decision = self.command_policy.check_argv(argv)
                if not decision.allowed:
                    return ToolResult(
                        call_id=call_id,
                        name=self.name,
                        success=False,
                        output="",
                        error=f"Command blocked by policy: {decision.reason}",
                    )
            try:
                proc = await asyncio.create_subprocess_exec(
                    *argv,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=str(ctx.workspace_root),
                    env=env,
                )
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=self.timeout_seconds
                )
                exit_code = proc.returncode
            except asyncio.TimeoutError:
                timed_out = True
            except Exception as e:
                duration_ms = (time.monotonic() - start) * 1000
                self._emit_command_event(
                    ctx,
                    mode=mode,
                    exit_code=None,
                    duration_ms=duration_ms,
                    timed_out=False,
                    success=False,
                )
                return ToolResult(
                    call_id=call_id,
                    name=self.name,
                    success=False,
                    output="",
                    error=str(e),
                )
        else:
            if self.command_policy:
                decision = self.command_policy.check(command)
                if not decision.allowed:
                    return ToolResult(
                        call_id=call_id,
                        name=self.name,
                        success=False,
                        output="",
                        error=f"Command blocked by policy: {decision.reason}",
                    )
            try:
                proc = await asyncio.create_subprocess_shell(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=str(ctx.workspace_root),
                    env=env,
                )
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=self.timeout_seconds
                )
                exit_code = proc.returncode
            except asyncio.TimeoutError:
                timed_out = True
            except Exception as e:
                duration_ms = (time.monotonic() - start) * 1000
                self._emit_command_event(
                    ctx,
                    mode=mode,
                    exit_code=None,
                    duration_ms=duration_ms,
                    timed_out=False,
                    success=False,
                )
                return ToolResult(
                    call_id=call_id,
                    name=self.name,
                    success=False,
                    output="",
                    error=str(e),
                )

        duration_ms = (time.monotonic() - start) * 1000
        if timed_out:
            self._emit_command_event(
                ctx,
                mode=mode,
                exit_code=None,
                duration_ms=duration_ms,
                timed_out=True,
                success=False,
            )
            return ToolResult(
                call_id=call_id,
                name=self.name,
                success=False,
                output=self._append_execution_meta(
                    "",
                    exit_code=None,
                    duration_ms=duration_ms,
                    timed_out=True,
                ),
                error=f"Command timed out after {self.timeout_seconds}s",
            )

        output = stdout.decode("utf-8", errors="replace")
        error_output = stderr.decode("utf-8", errors="replace")
        combined = output
        if error_output:
            combined += f"\n[stderr]\n{error_output}"
        combined = combined.strip() or "(no output)"
        combined = self._append_execution_meta(
            combined,
            exit_code=exit_code,
            duration_ms=duration_ms,
            timed_out=False,
        )

        max_chars = ctx.tool_output_max_chars
        if max_chars is not None and len(combined) > max_chars:
            combined = combined[:max_chars] + "\n... (output truncated)"

        success = exit_code == 0
        self._emit_command_event(
            ctx,
            mode=mode,
            exit_code=exit_code,
            duration_ms=duration_ms,
            timed_out=False,
            success=success,
        )
        return ToolResult(
            call_id=call_id,
            name=self.name,
            success=success,
            output=combined,
        )
