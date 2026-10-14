import json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"D:\crq\src\coding-harness\runs")
for rel in ["step2-b0b/pytest-dev__pytest-5103", "step2-b0c/pytest-dev__pytest-5221", "step2-b0c/pytest-dev__pytest-5227"]:
    d = ROOT / rel
    print("=" * 20, rel)
    print(json.dumps(json.loads((d / "summary.json").read_text(encoding="utf-8")), ensure_ascii=False)[:600])
    ev = d / "events.jsonl"
    if not ev.exists():
        print("no events"); continue
    types = {}
    rows = [json.loads(l) for l in ev.read_text(encoding="utf-8").splitlines() if l.strip()]
    for r in rows:
        types[r.get("event_type")] = types.get(r.get("event_type"), 0) + 1
    print("event types:", types)
    for r in rows:
        t = r.get("event_type")
        p = r.get("payload") or {}
        if t in ("tool.intent", "tool.started"):
            args = p.get("arguments") or p.get("args") or p.get("params") or {}
            print(f"  seq={r.get('seq')} step={p.get('step')} {p.get('tool') or p.get('name')} {json.dumps(args, ensure_ascii=False)[:160]}")
        elif t in ("model.completed",):
            txt = (p.get("text") or p.get("content") or "")
            if txt:
                print(f"  [model text] {str(txt)[:200]!r}")
        elif t in ("run.finished", "run.failed"):
            print("  FINISH", json.dumps(p, ensure_ascii=False)[:400])
