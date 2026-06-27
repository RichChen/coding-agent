"""Pydantic 配置 schema — YAML 加载后校验。

English: typed config models with validation. Unknown fields are forbidden
so typos in YAML keys surface as clear errors.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class LLMConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base_url: str
    api_key: str = ""
    model: str = "deepseek-v4-pro"
    temperature: float = 0.0
    max_tokens: int = 4096


class RetryConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_retries: int = 2
    backoff_base_seconds: float = 1.0
    backoff_factor: float = 2.0
    retry_on: list[str] = Field(default_factory=lambda: ["timeout", "model_error"])


class RuntimeContextConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    micro_compact: bool = False
    keep_recent_tool_results: int = 3
    compact_token_threshold: int | None = None


class RuntimePlannerConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = False


class RuntimeSubagentsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    max_depth: int = 1
    readonly: bool = True
    max_steps: int = 3


class RuntimeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: str = "react"
    max_steps: int = 30
    step_timeout_seconds: int = 120
    total_timeout_seconds: int = 600
    system_prompt_path: str | None = None
    context: RuntimeContextConfig = Field(default_factory=RuntimeContextConfig)
    planner: RuntimePlannerConfig = Field(default_factory=RuntimePlannerConfig)
    subagents: RuntimeSubagentsConfig = Field(default_factory=RuntimeSubagentsConfig)


class SandboxConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deny_absolute_paths: bool = True
    deny_parent_traversal: bool = True
    workspace_root: str | None = None


class CommandConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allow_all: bool = True
    allowed_prefixes: list[str] = Field(default_factory=list)
    blocked_patterns: list[str] = Field(default_factory=list)
    prefer_argv: bool = False
    env_whitelist: list[str] = Field(default_factory=list)
    timeout_seconds: int = 30


class PolicyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sandbox: SandboxConfig = Field(default_factory=SandboxConfig)
    command: CommandConfig = Field(default_factory=CommandConfig)
    file_size_limit_bytes: int | None = None
    tool_output_max_chars: int | None = None
    read_file_max_lines: int | None = None


class ToolsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: list[str] = Field(default_factory=lambda: ["read_file", "write_file", "list_dir"])


class TracingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format: str = "jsonl"
    output_dir: str = "traces"
    lifecycle_events: bool = False
    llm_stream_events: bool = False


class HarnessConfig(BaseModel):
    """Top-level harness configuration with validation."""

    model_config = ConfigDict(extra="forbid")

    llm: LLMConfig
    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)
    retry: RetryConfig = Field(default_factory=RetryConfig)
    policy: PolicyConfig = Field(default_factory=PolicyConfig)
    tools: ToolsConfig = Field(default_factory=ToolsConfig)
    tracing: TracingConfig = Field(default_factory=TracingConfig)
