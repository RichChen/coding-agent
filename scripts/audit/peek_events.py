import json, sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
path = Path(sys.argv[1])
limit = int(sys.argv[2]) if len(sys.argv) > 2 else 400
rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
print("events:", len(rows))
print("types:", Counter(r.get("type") or r.get("kind") or r.get("event") for r in rows).most_common(30))
for r in rows[:6]:
    print(json.dumps(r, ensure_ascii=False)[:limit])
    print("...")
