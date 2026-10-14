import json, sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"D:\crq\src\coding-harness")
d = ROOT / "docs/sprint/main-calibration"
reasons = Counter()
rows = []
for f in sorted(d.glob("*.json")):
    j = json.loads(f.read_text(encoding="utf-8"))
    n = j.get("nodeids") or {}
    f2 = n.get("f2p") or {}
    p2 = n.get("p2p") or {}
    for side, rs in (n.get("dropped_reasons") or {}).items():
        for k, v in rs.items():
            reasons[(side, k)] += v
    acc = j.get("accepted")
    f2p_drop = (f2.get("original") or 0) - (f2.get("used") or 0)
    p2p_o, p2p_u = p2.get("original") or 0, p2.get("used") or 0
    excl = j.get("p2p_excluded_count") or 0
    rows.append((j["task_id"], acc, f2.get("original"), f2.get("used"), p2p_o, p2p_u, excl, j.get("empty_f2p"), j.get("gold_f2p"), j.get("reason")))
print("drop reasons:", {f"{a}:{b}": v for (a, b), v in reasons.items()})
print("\nid | acc | F2P orig/used | P2P orig/used | p2p_excl(gold-fail) | empty_f2p | gold_f2p")
for r in rows:
    flag = ""
    if r[1] and r[2] is not None and r[3] is not None and r[3] < r[2]:
        flag += " F2P_DROPPED"
    if r[1] and r[4] and (r[5] - r[6]) < 0.8 * r[4]:
        flag += " P2P_SHRUNK"
    if flag or not r[1]:
        print(" ", r, flag)
print("\naccepted:", sum(1 for r in rows if r[1]), "of", len(rows))
