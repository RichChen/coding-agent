import json, sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"D:\crq\src\coding-harness\runs\sprint4-b0-v2")
EDIT = {"edit_file", "search_replace", "write_file"}


def resolve(v, arts):
    if isinstance(v, dict) and set(v) == {"artifact_ref"}:
        p = arts / v["artifact_ref"]["path"]
        return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {"_missing": True}
    return v


for tid, rep in [("sympy__sympy-11897", "r1"), ("sympy__sympy-11897", "r2"), ("pytest-dev__pytest-5103", "r3"), ("sympy__sympy-11400", "r2")]:
    run = ROOT / tid / rep
    arts = run / "session/artifacts"
    rows = [json.loads(l) for l in (run / "events.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    names = Counter()
    edits = []
    results = {}
    for e in rows:
        p = resolve(e.get("payload"), arts) or {}
        if e.get("event_type") == "tool.intent":
            n = p.get("name")
            names[n] += 1
            if n in EDIT:
                a = resolve(p.get("arguments"), arts) or {}
                edits.append((p.get("call_id") or p.get("tool_call_id") or p.get("intent_id"), a.get("path")))
        if e.get("event_type") == "tool.result":
            s = json.dumps(p, ensure_ascii=False)
            results[len(results)] = s
    s = json.loads((run / "summary.json").read_text(encoding="utf-8"))
    print(f"== {tid} {rep}: tools={dict(names)} edits={edits[:6]} status={s.get('status')} snapshot_error={s.get('snapshot_error')} stop={s.get('stop_reason')}")
    # show edit results
    shown = 0
    for e in rows:
        if e.get("event_type") == "tool.result":
            p = resolve(e.get("payload"), arts) or {}
            txt = json.dumps(p, ensure_ascii=False)
            if any(k in txt[:600] for k in ("search_replace", "edit_file", "write_file")):
                print("   result:", txt[:400])
                shown += 1
                if shown >= 3:
                    break
    delta = run / "candidate-delta.json"
    if delta.exists():
        d = json.loads(delta.read_text(encoding="utf-8"))
        print("   delta changed:", list((d.get("changed") or {}).keys())[:5], "deleted:", (d.get("deleted") or [])[:5])
