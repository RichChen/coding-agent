import json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"D:\crq\src\coding-harness\runs\sprint2-b0")
EDIT = {"edit_file", "search_replace", "write_file"}

for d in sorted(p for p in ROOT.iterdir() if p.is_dir()):
    s = json.loads((d / "summary.json").read_text(encoding="utf-8"))
    delta_path = d / "candidate-delta.json"
    changed = []
    if delta_path.exists():
        delta = json.loads(delta_path.read_text(encoding="utf-8"))
        changed = sorted((delta.get("changed") or {}).keys())
    so = [c for c in changed if c.endswith(".so")]
    src = [c for c in changed if not c.endswith(".so")]
    print(f"== {d.name}: solved={s.get('solved')} status={s.get('status') or s.get('grader_status')} "
          f"stop={s.get('stop_reason')} changed={len(changed)} so={len(so)} non_so={src[:6]}")
    if s.get("snapshot_error"):
        print("   snapshot_error:", s["snapshot_error"][:300])

d = ROOT / "sympy__sympy-11870"
rows = [json.loads(l) for l in (d / "events.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
results = {}
for r in rows:
    if r.get("event_type") == "tool.result":
        p = r.get("payload") or {}
        results[p.get("call_id") or p.get("tool_call_id")] = p
print("\n== sympy-11870 edit intents")
for r in rows:
    p = r.get("payload") or {}
    if r.get("event_type") == "tool.intent" and (p.get("tool") or p.get("name")) in EDIT:
        cid = p.get("call_id") or p.get("tool_call_id")
        res = results.get(cid, {})
        args = p.get("arguments") or p.get("args") or {}
        print(" ", p.get("tool") or p.get("name"), args.get("path"),
              "| result:", json.dumps({k: res.get(k) for k in ("status", "success", "error")}, ensure_ascii=False)[:200])
