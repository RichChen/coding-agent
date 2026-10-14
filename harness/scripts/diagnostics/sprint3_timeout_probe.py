"""Zero-model check: sleep 200 must time out inside the tool, not the step."""
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_swe_task import ROOT as RUN_ROOT
from scripts.run_swe_task import load_yaml, run_task
from src.llm.client import LLMResponse, ToolCall


class _SleepThenStop:
    """Stand-in assigned over the runner mock. Records the tool result."""

    def __init__(self):
        self.model = "mock-model"
        self.supports_streaming = False
        self._owns_http_client = False
        self._http = None
        self._closed = False
        self.calls = 0
        self.tool_text = ""

    async def chat(self, messages, tools=None):
        self.calls += 1
        if self.calls == 1:
            return LLMResponse(
                text="",
                tool_calls=[ToolCall(id="sleep-1", name="run_command", arguments={"command": "sleep 200"})],
                finish_reason="tool_calls",
                usage={"prompt_tokens": 0, "completion_tokens": 0, "provenance": "unknown"},
            )
        for message in messages:
            content = message.get("content")
            if isinstance(content, str) and "run_command" in content or (isinstance(content, str) and "超时" in content):
                self.tool_text = content
            if isinstance(content, list):
                self.tool_text += json.dumps(content, ensure_ascii=False)
        return LLMResponse(
            text="mock finish after timeout",
            finish_reason="stop",
            usage={"prompt_tokens": 0, "completion_tokens": 0, "provenance": "unknown"},
        )

    async def stream_chat(self, messages, tools=None):
        from src.llm.client import LLMStreamEvent, StreamCapability
        response = await self.chat(messages, tools)
        yield LLMStreamEvent(
            "llm_stream_done",
            {
                "finish_reason": response.finish_reason,
                "usage": response.usage,
                "has_tool_calls": response.has_tool_calls,
                "capability": StreamCapability.NON_STREAMING.value,
                "response": response,
            },
        )

    async def aclose(self):
        self._closed = True


async def main():
    manifest = load_yaml(RUN_ROOT / "configs/sprint/dev-tasks.yaml")
    task = next(item for item in manifest["tasks"] if item["id"] == "sympy__sympy-11870")
    out = RUN_ROOT / "runs/sprint3-timeout"
    if out.exists():
        import shutil
        shutil.rmtree(out)
    llm = _SleepThenStop()
    import scripts.run_swe_task as runner
    original = runner._MockLLM
    runner._MockLLM = lambda: llm
    try:
        summary = await run_task(task, RUN_ROOT / "configs/sprint/b0-v1.yaml", out, mock=True)
    finally:
        runner._MockLLM = original
    print(json.dumps({
        "stop_reason": summary.get("stop_reason"),
        "status": summary.get("status"),
        "calls": llm.calls,
        "saw_timeout": "超时" in llm.tool_text,
        "tool_text": llm.tool_text[:400],
    }, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
