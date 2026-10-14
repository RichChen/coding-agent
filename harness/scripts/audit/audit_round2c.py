import json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"D:\crq\src\coding-harness\runs\sprint2-b0")

for t in ["scikit-learn__scikit-learn-10297", "scikit-learn__scikit-learn-11281"]:
    g = json.loads((ROOT / t / "grader-result.json").read_text(encoding="utf-8"))
    print("==", t, {k: g.get(k) for k in ("status", "reason", "execution_status", "f2p_passed", "p2p_passed", "p2p_total", "receipt_complete")})
    cases = g.get("cases") or []
    print("  outcomes:", {o: sum(1 for c in cases if c.get("outcome") == o) for o in {c.get("outcome") for c in cases}})
    print("  sample:", json.dumps(cases[:2], ensure_ascii=False)[:400])

d = ROOT / "sympy__sympy-11870"
arts = list(d.rglob("61d6c97d91084cdb61475f5bf150bf4aac202973c36a75ad9cd9148c6562c7be*"))
print("\n== artifact files:", [str(a) for a in arts][:3])
if arts:
    data = json.loads(arts[0].read_text(encoding="utf-8"))
    print("keys:", list(data.keys())[:30] if isinstance(data, dict) else type(data))
    if isinstance(data, dict):
        for k in ("failure_reason", "stop_reason", "success", "termination_kind", "final_answer"):
            print(" ", k, "=", str(data.get(k))[:300])
        snap = data.get("snapshot_error") or data.get("execution") or None
        print("  snapshot-ish:", str(snap)[:300])
        for k, v in data.items():
            if "snapshot" in k or "delta" in k or "cleanup" in k:
                print("  ", k, "=", str(v)[:300])
