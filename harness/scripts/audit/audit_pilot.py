import json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"D:\crq\src\coding-harness")
rows = [json.loads(l) for l in (ROOT / "runs/sprint3-pilot-calibrate/results.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
print("keys:", list(rows[0].keys()))
for r in rows:
    print(r["id"], "acc", r.get("accepted"), "f2p", r.get("f2p_total"), "empty_f2p", r.get("empty_f2p"), "gold_f2p", r.get("gold_f2p"),
          "p2p", r.get("empty_p2p"), "/", r.get("empty_p2p_total"), "gold_p2p", r.get("gold_p2p"),
          "| img", str(r.get("image"))[:60], "| er", str(r.get("empty_reason"))[:70], "| gr", str(r.get("gold_reason"))[:70], "| note", str(r.get("note") or r.get("status"))[:60])
