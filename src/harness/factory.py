"""Agent 装配工厂：配置加载 + AgentLoop 构建。

English: single source of truth for loading YAML configs and assembling AgentLoop instances.
No business logic — pure wiring.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import yaml

from src.config.schema import HarnessConfig
from src.llm.client import LLMClient
from src.policy.budget import Budget
from src.policy.rules import CommandPolicy
from src.policy.sandbox import Sandbox
from src.runtime.loop import AgentLoop
from src.runtime.context import ContextPolicyConfig, build_context_hooks
from src.runtime.planner import SimplePlanner
from src.runtime.retry import RetryConfig
from src.tools.command import RunCommandTool
from src.tools.edit import EditFileTool
from src.tools.files import ListDirTool, ReadFileTool, WriteFileTool
from src.tools.patch import SearchReplaceTool
from src.tools.registry import ToolRegistry
from src.tracing.events import EventBus
from src.tracing.logger import TraceLogger


def _load_dotenv_if_present(dotenv_path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not dotenv_path.exists():
        return values

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def load_config(config_path: str | Path) -> dict:
    """Load a YAML config file with ${VAR:default} env-var substitution.

    Validates against HarnessConfig schema — unknown keys or wrong types
    raise pydantic ValidationError with a clear field path.
    """
    config_path = Path(config_path)
    dotenv_values = _load_dotenv_if_present(config_path.parent.parent / ".env")

    with open(config_path, encoding="utf-8") as f:
        raw = f.read()

    def resolve_env(match):
        var = match.group(1)
        default = match.group(2) if match.lastindex >= 2 else ""
        return os.environ.get(var, dotenv_values.get(var, default))

    raw = re.sub(r"\$\{(\w+):?([^}]*)\}", resolve_env, raw)
    data = yaml.safe_load(raw)
    # Validate and return as dict (not model instance) for backwards compat
    return HarnessConfig.model_validate(data).model_dump()


def build_agent(
    config: dict,
    workspace: Path,
    *,
    tracer: TraceLogger | None = None,
    event_bus: EventBus | None = None,
) -> AgentLoop:
    """Assemble an AgentLoop from a config dict and workspace.

    This is pure wiring — no side effects beyond object construction.
    """
    llm_cfg = config["llm"]
    rt_cfg = config["runtime"]
    retry_cfg = config.get("retry", {})
    policy_cfg = config.get("policy", {})
    tools_cfg = config.get("tools", {})

    llm = LLMClient(
        base_url=llm_cfg["base_url"],
        api_key=llm_cfg["api_key"],
        model=llm_cfg["model"],
        temperature=llm_cfg.get("temperature", 0.0),
        max_tokens=llm_cfg.get("max_tokens", 4096),
    )

    sandbox = Sandbox(
        workspace_root=workspace,
        deny_absolute=policy_cfg.get("sandbox", {}).get("deny_absolute_paths", True),
        deny_parent_traversal=policy_cfg.get("sandbox", {}).get("deny_parent_traversal", True),
    )

    budget = Budget(
        max_steps=rt_cfg["max_steps"],
        total_timeout_seconds=rt_cfg["total_timeout_seconds"],
        step_timeout_seconds=rt_cfg["step_timeout_seconds"],
    )

    retry = RetryConfig(
        max_retries=retry_cfg.get("max_retries", 2),
        backoff_base_seconds=retry_cfg.get("backoff_base_seconds", 1.0),
        backoff_factor=retry_cfg.get("backoff_factor", 2.0),
        retry_on=retry_cfg.get("retry_on", ["timeout", "model_error"]),
    )

    tools = ToolRegistry()
    enabled = tools_cfg.get("enabled", ["read_file", "write_file", "list_dir"])
    if "read_file" in enabled:
        tools.register(ReadFileTool())
    if "write_file" in enabled:
        tools.register(WriteFileTool())
    if "list_dir" in enabled:
        tools.register(ListDirTool())
    if "run_command" in enabled:
        cmd_cfg = policy_cfg.get("command", {})
        cmd_policy = CommandPolicy(
            allow_all=cmd_cfg.get("allow_all", True),
            allowed_prefixes=cmd_cfg.get("allowed_prefixes", []),
            blocked_patterns=cmd_cfg.get("blocked_patterns", []),
        )
        tools.register(
            RunCommandTool(
                command_policy=cmd_policy,
                timeout_seconds=cmd_cfg.get("timeout_seconds", 30),
                env_whitelist=cmd_cfg.get("env_whitelist", []),
                prefer_argv=cmd_cfg.get("prefer_argv", False),
            )
        )
    if "search_replace" in enabled:
        tools.register(SearchReplaceTool())
    if "edit_file" in enabled:
        tools.register(EditFileTool())

    subagent_cfg = rt_cfg.get("subagents", {})
    if subagent_cfg.get("enabled"):
        if "subagent_task" not in enabled:
            raise ValueError(
                "runtime.subagents.enabled=true requires tools.enabled to include subagent_task"
            )
        from src.tools.subagent import SubagentTaskTool
        tools.register(
            SubagentTaskTool(
                llm=llm,
                output_dir=config.get("tracing", {}).get("output_dir", "traces"),
                max_depth=subagent_cfg.get("max_depth", 1),
                readonly=subagent_cfg.get("readonly", True),
                max_steps=subagent_cfg.get("max_steps", 3),
                total_timeout_seconds=rt_cfg.get("step_timeout_seconds", 60),
                step_timeout_seconds=rt_cfg.get("step_timeout_seconds", 60),
                file_size_limit_bytes=policy_cfg.get("file_size_limit_bytes"),
                tool_output_max_chars=policy_cfg.get("tool_output_max_chars"),
                read_file_max_lines=policy_cfg.get("read_file_max_lines"),
            )
        )

    # System prompt: load from file if path configured
    system_prompt = None
    prompt_path = rt_cfg.get("system_prompt_path")
    if prompt_path:
        resolved_prompt = Path(prompt_path)
        if not resolved_prompt.is_absolute():
            resolved_prompt = Path.cwd() / resolved_prompt
        if resolved_prompt.exists():
            system_prompt = resolved_prompt.read_text(encoding="utf-8").strip()
        else:
            raise FileNotFoundError(f"System prompt file not found: {resolved_prompt}")

    # Context policy: L0 limits are carried by ToolContext; L1 uses hooks.
    ctx_cfg = rt_cfg.get("context", {})
    context_policy = ContextPolicyConfig.from_runtime_config(ctx_cfg, policy_cfg)
    hooks = build_context_hooks(context_policy)

    runtime_mode = rt_cfg.get("mode", "react")
    planner = None
    planner_cfg = rt_cfg.get("planner", {})
    if runtime_mode == "plan_act" and planner_cfg.get("enabled"):
        planner = SimplePlanner()

    # EventBus: create if lifecycle_events is enabled in tracing config
    tracing_cfg = config.get("tracing", {})
    if event_bus is None:
        if tracing_cfg.get("lifecycle_events"):
            event_bus = EventBus(output_dir=tracing_cfg.get("output_dir", "traces"))

    # read_events tool (debug only — not in baseline/hardened)
    if "read_events" in enabled:
        from src.tools.events import ReadEventsTool
        read_events_tool = ReadEventsTool(event_bus=event_bus)
        tools.register(read_events_tool)

    return AgentLoop(
        llm=llm,
        tools=tools,
        sandbox=sandbox,
        budget=budget,
        retry_config=retry,
        tracer=tracer,
        enabled_tools=enabled,
        file_size_limit_bytes=policy_cfg.get("file_size_limit_bytes"),
        tool_output_max_chars=policy_cfg.get("tool_output_max_chars"),
        read_file_max_lines=policy_cfg.get("read_file_max_lines"),
        hooks=hooks,
        event_bus=event_bus,
        system_prompt=system_prompt,
        runtime_mode=runtime_mode,
        planner=planner,
        use_llm_stream=tracing_cfg.get("llm_stream_events", False),
    )
