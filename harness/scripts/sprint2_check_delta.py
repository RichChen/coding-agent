"""Zero-model check: baseline image copy, then search_replace plus a changelog, both land in the delta."""
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.execution.baseline_image_backend import BaselineImageBackend
from src.tools.base import ToolContext
from src.tools.container_files import ContainerFileTool
from src.tools.files import WriteFileTool
from src.tools.patch import SearchReplaceTool


async def check(image: str, label: str, import_code: str) -> None:
    backend = BaselineImageBackend(
        image=image, context="desktop-linux", memory_bytes=1024**3,
        workspace_bytes=256 * 1024**2, tmpfs_bytes=64 * 1024**2, network="none",
    )
    ctx = ToolContext(workspace_root=Path("/workspace"), call_id="check")
    try:
        await backend.start()
        probe = await backend._ok(
            "exec", backend.name, "/usr/local/bin/python", "-I", "-c", import_code, limit=64 * 1024, timeout=60,
        )
        replaced = await ContainerFileTool(SearchReplaceTool(), backend).execute(
            {"path": "sprint2-probe.txt", "search": "absent", "replace": "present"}, ctx,
        )
        if not replaced.success:
            await ContainerFileTool(WriteFileTool(), backend).execute(
                {"path": "sprint2-probe.txt", "content": "absent\n"}, ctx,
            )
            replaced = await ContainerFileTool(SearchReplaceTool(), backend).execute(
                {"path": "sprint2-probe.txt", "search": "absent", "replace": "present"}, ctx,
            )
        written = await ContainerFileTool(WriteFileTool(), backend).execute(
            {"path": "changelog/sprint2-check.rst", "content": "check\n"}, ctx,
        )
        delta = await backend.export_delta()
        names = sorted((delta.get("changed") or {}).keys())
        print(json.dumps({
            "label": label,
            "import": probe.decode("utf-8", "replace").strip()[:200],
            "replace_ok": replaced.success,
            "write_ok": written.success,
            "changed": names,
        }), flush=True)
        missing = [name for name in ("sprint2-probe.txt", "changelog/sprint2-check.rst") if name not in names]
        if missing or not replaced.success or not written.success:
            raise SystemExit("delta missing " + ",".join(missing))
    finally:
        await backend.close()


def main() -> None:
    receipt = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    asyncio.run(check(receipt["baseline_image_digest"], sys.argv[2], sys.argv[3]))


if __name__ == "__main__":
    main()
