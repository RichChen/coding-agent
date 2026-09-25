"""Print a short pilot-calibration table. No model calls."""
import json
from pathlib import Path

rows = [
    json.loads(line)
    for line in Path("runs/sprint3-pilot-calibrate/results.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip()
]
for row in rows:
    reason = row.get("reason") or row.get("empty_reason") or ""
    if "cannot stat '/opt/repo" in reason:
        kind = "image_has_no_repo"
    elif row.get("reason") == "contract_blocker":
        kind = "contract_blocker"
    elif row.get("accepted"):
        kind = "accepted"
    elif row.get("empty_f2p") and row.get("empty_f2p") == row.get("gold_f2p"):
        kind = "empty_already_passes"
    else:
        kind = "gold_failed"
    print(f"{row['id']} {kind} empty={row.get('empty_f2p')}/{row.get('f2p_total')} gold={row.get('gold_f2p')} p2p={row.get('empty_p2p')}/{row.get('gold_p2p')}")
