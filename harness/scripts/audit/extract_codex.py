import json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
base = Path(r"C:\Users\Administrator\.codex\sessions\2026\09\25")
files = sorted(base.glob("*01a0d7ca-98a0-77d1-8b03-8c8c7a671a76*.jsonl"))
out = Path(r"d:\crq\src\coding-harness\.tmp\codex_01a0d7ca.txt")
lines = []
for f in files:
    lines.append(f"##### FILE {f.name}")
    for raw in f.read_text(encoding="utf-8").splitlines():
        try:
            e = json.loads(raw)
        except Exception:
            continue
        t = e.get("type")
        p = e.get("payload") or {}
        if t == "session_meta":
            lines.append("[meta] " + json.dumps({k: p.get(k) for k in ("id", "cwd", "model", "originator", "source")}, ensure_ascii=False)[:400])
        elif t == "response_item":
            pt = p.get("type")
            if pt == "message":
                role = p.get("role")
                text = "".join(c.get("text", "") for c in p.get("content") or [] if isinstance(c, dict))
                if role in ("user", "assistant") and text.strip():
                    if role == "user" and (text.startswith("<environment_context>") or text.startswith("# AGENTS.md") or "<permissions" in text[:200]):
                        lines.append(f"[{role}-ctx] {text[:300]}")
                    else:
                        lines.append(f"[{role}] {text}")
            elif pt == "function_call":
                lines.append(f"[call {p.get('name')}] {str(p.get('arguments'))[:400]}")
            elif pt == "function_call_output":
                lines.append(f"[out] {str(p.get('output'))[:300]}")
            elif pt == "reasoning":
                s = " ".join(x.get("text", "") for x in p.get("summary") or [] if isinstance(x, dict))
                if s:
                    lines.append(f"[reasoning] {s[:600]}")
        elif t == "turn_context":
            lines.append("[turn_ctx] " + json.dumps({k: p.get(k) for k in ("cwd", "model", "effort")}, ensure_ascii=False))
out.write_text("\n".join(lines), encoding="utf-8")
print(len(lines), out)
