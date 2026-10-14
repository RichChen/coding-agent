import json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"D:\crq\src\coding-harness")
m = __import__("yaml").safe_load((ROOT / "configs/sprint/dev-tasks.yaml").read_text(encoding="utf-8"))
tasks = {t["id"]: t for t in m["tasks"]}

CHECKS = {
    "sympy__sympy-11400": ("sympy/printing/tests/test_ccode.py", "def test_ccode_sinc"),
    "scikit-learn__scikit-learn-10949": ("sklearn/utils/tests/test_validation.py", "def test_check_dataframe_warns_on_dtype"),
    "django__django-11039": ("tests/migrations/test_commands.py", "test_sqlmigrate_for_non_transactional_databases"),
}
for tid, (rel, needle) in CHECKS.items():
    t = tasks[tid]
    orig = ROOT / t["original"] / rel
    base = ROOT / t["baseline"] / rel
    has = lambda p: p.is_file() and needle in p.read_text(encoding="utf-8", errors="replace")
    print(f"{tid}: original has={has(orig)} baseline(has test patch?)={has(base)}")

def resolve(v, arts):
    if isinstance(v, dict) and set(v) == {"artifact_ref"}:
        p = arts / v["artifact_ref"]["path"]
        return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None
    return v

for tid, (rel, needle) in CHECKS.items():
    name = needle.replace("def ", "")
    run = ROOT / "runs/sprint3-b0" / tid / "r1"
    if not run.exists():
        run = ROOT / "runs/sprint2-b0" / tid
    arts = run / "session/artifacts"
    rows = [json.loads(l) for l in (run / "events.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    hits = 0
    for e in rows:
        if e.get("event_type") not in ("tool.intent", "tool.result"):
            continue
        p = resolve(e.get("payload"), arts)
        s = json.dumps(p, ensure_ascii=False) if p is not None else ""
        if name in s:
            hits += 1
            if hits <= 3:
                i = s.find(name)
                print(f"  [{tid} {e['event_type']}] ...{s[max(0, i - 250): i + 250]}...")
    print(f"  {tid}: events mentioning {name}: {hits}  (run {run.relative_to(ROOT)})")
