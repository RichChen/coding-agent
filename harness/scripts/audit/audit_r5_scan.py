import json, sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"D:\crq\src\coding-harness")
d = ROOT / "docs/sprint/clean-images"
import yaml
pool = yaml.safe_load((ROOT / "configs/sprint/main-targets.yaml").read_text(encoding="utf-8"))
ids = [t["id"] for t in (pool.get("tasks") or pool)]
print("pool", len(ids))
tot_inst = tot_base = 0
suspicious = []
for tid in ids:
    p = d / f"{tid}.json"
    if not p.exists():
        print("  no image json:", tid)
        continue
    j = json.loads(p.read_text(encoding="utf-8"))
    fs = j.get("filesystem_scan") or {}
    inst = fs.get("install_record_same") or []
    base = fs.get("base_image_same") or []
    tot_inst += fs.get("install_record_same_count") or 0
    tot_base += fs.get("base_image_same_count") or 0
    proj = tid.split("__")[1].split("-")[0].replace("scikit", "sklearn")
    names = {"django": "django", "sympy": "sympy", "sklearn": "sklearn", "sphinx": "sphinx", "pytest": "_pytest"}
    key = names.get(proj, proj)
    bad = [x for x in inst + base if f"/{key}/" in x or f"/{key}-" in x or x.startswith("/opt/repo") or x.startswith("/workspace")]
    if inst or base:
        print(f"  {tid}: install_same={fs.get('install_record_same_count')} base_same={fs.get('base_image_same_count')} hits={fs.get('hit_count')} sample={(inst + base)[:3]}")
    if bad:
        suspicious.append((tid, bad[:5]))
print("totals install_same", tot_inst, "base_same", tot_base)
print("SUSPICIOUS (project package paths excluded):")
for s in suspicious:
    print(" ", s)
