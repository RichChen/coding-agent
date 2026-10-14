import json, sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
path = Path(sys.argv[1])
mode = sys.argv[2] if len(sys.argv) > 2 else "summary"
rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
types = Counter(r["event_type"] for r in rows)
if mode == "types":
    print(types.most_common())
    sys.exit()

# last state.saved has the full message list
states = [r for r in rows if r["event_type"] == "state.saved" and "messages" in (r.get("payload") or {})]
if mode == "keys":
    for r in rows:
        if r["event_type"] == "state.saved":
            print(list((r.get("payload") or {}).keys()))
    sys.exit()
msgs = states[-1]["payload"]["messages"] if states else []
if mode == "prompt":
    for m in msgs[:2]:
        print("=== ROLE", m.get("role"))
        c = m.get("content")
        print(c if isinstance(c, str) else json.dumps(c, ensure_ascii=False)[:6000])
    sys.exit()

width = int(sys.argv[3]) if len(sys.argv) > 3 else 300
for i, m in enumerate(msgs):
    role = m.get("role")
    if role == "system" or (role == "user" and i < 2):
        continue
    if role == "assistant":
        text = m.get("content")
        if isinstance(text, str) and text.strip():
            print(f"[{i}] A-text: {text.strip()[:width]}")
        for tc in m.get("tool_calls") or []:
            fn = tc.get("function") or tc
            print(f"[{i}] CALL {fn.get('name')} {str(fn.get('arguments'))[:width]}")
    elif role == "tool":
        c = m.get("content")
        c = c if isinstance(c, str) else json.dumps(c, ensure_ascii=False)
        print(f"[{i}] RESULT {c[:width]!r}")
    else:
        c = m.get("content")
        c = c if isinstance(c, str) else json.dumps(c, ensure_ascii=False)
        print(f"[{i}] {role}: {c[:width]!r}")
