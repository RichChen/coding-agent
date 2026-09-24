# CLAUDE.md

## Reference Project

The project at `D:\crq\src\learn-claude-code-main` is the primary reference for this work. It teaches harness engineering for Claude Code — the model IS the agent, and the surrounding code is the harness.

### When to consult it
- When implementing agent loops, tool use patterns, or harness infrastructure
- When unsure about Claude Code skill/hook/MCP conventions
- Before writing new agent-related code — check if the reference has a relevant example

### Structure
| Directory | Purpose |
|-----------|---------|
| `agents/` | 12 progressive scripts (`s01`–`s12`) + combined `s_full.py` (43KB reference implementation) |
| `docs/en/` | English lesson docs (s01–s12) |
| `docs/zh/` | Chinese lesson docs (s01–s12) |
| `skills/` | Reusable skill definitions: agent-builder, code-review, mcp-builder, pdf |
| `tests/` | Smoke tests for agent scripts and s_full |
| `web/` | Next.js companion app |

### Key files
- `agents/s_full.py` — all-in-one reference (43KB)
- `skills/agent-builder/SKILL.md` — example of a well-structured skill definition
- `skills/code-review/SKILL.md` — code review skill reference
