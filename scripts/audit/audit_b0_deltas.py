import json, re, sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"D:\crq\src\coding-harness")
runs = ROOT / "runs" / "a5-main"
INFRA = re.compile(r"(^|/)(conftest\.py|runtests\.py|pytest\.ini|tox\.ini|setup\.cfg|setup\.py|pyproject\.toml|test_sqlite\.py|__init__\.py)$")


def is_test(path: str) -> bool:
    return bool(re.search(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_tests?\.py$|(^|/)conftest\.py$", path))


def patch_paths(text: str) -> set[str]:
    return set(re.findall(r"^\+\+\+ b/(\S+)", text or "", re.M))


rows = []
for summary_path in sorted(runs.glob("*/b0/r[123]/summary.json")):
    s = json.loads(summary_path.read_text(encoding="utf-8"))
    task = summary_path.parts[-4]
    delta_path = summary_path.parent / "candidate-delta.json"
    delta = json.loads(delta_path.read_text(encoding="utf-8")) if delta_path.is_file() else {}
    changed = set((delta.get("changed") or {}).keys()) | set(delta.get("deleted") or [])
    private = json.loads((ROOT / "runs" / "sprint5-main-private" / (task + ".json")).read_text(encoding="utf-8"))
    tp = patch_paths(private.get("test_patch"))
    gp = patch_paths(private.get("patch"))
    src = {p for p in changed if not is_test(p)}
    tests = changed - src
    infra = {p for p in changed if INFRA.search(p) and p not in gp}
    rows.append(dict(task=task, run=summary_path.parts[-2], solved=bool(s.get("solved")), changed=changed,
                     src=src, tests=tests, tests_outside_tp=tests - tp, infra=infra,
                     touches_gold_file=bool(src & gp)))

solved = [r for r in rows if r["solved"]]
print("runs", len(rows), "solved", len(solved))
print("solved with no source change:", [(r["task"], r["run"], sorted(r["changed"])) for r in solved if not r["src"]])
print("solved not touching any gold-patch file:", len([r for r in solved if not r["touches_gold_file"]]))
for r in solved:
    if not r["touches_gold_file"]:
        print("   ", r["task"], r["run"], sorted(r["src"])[:4])
print("runs changing test-infra files (not in gold):")
for r in rows:
    if r["infra"]:
        print("   ", r["task"], r["run"], "solved" if r["solved"] else "fail", sorted(r["infra"]))
print("solved runs that edited tests outside the test patch:", sum(1 for r in solved if r["tests_outside_tp"]))
for r in solved:
    if r["tests_outside_tp"]:
        cal = json.loads((ROOT / "docs" / "sprint" / "main-calibration" / (r["task"] + ".json")).read_text(encoding="utf-8"))
        priv = json.loads((ROOT / "runs" / "sprint5-main-private" / (r["task"] + ".json")).read_text(encoding="utf-8"))
        ids = json.loads(priv["FAIL_TO_PASS"]) + json.loads(priv["PASS_TO_PASS"])
        hits = []
        for p in r["tests_outside_tp"]:
            stem = p.rsplit("/", 1)[-1].removesuffix(".py")
            mod = p.removesuffix(".py").replace("/", ".")
            if any(p in i or stem in i or mod.split("tests.", 1)[-1] in i for i in ids):
                hits.append(p)
        print("   outside-tp", r["task"], r["run"], sorted(r["tests_outside_tp"]), "graded-file-hit:", hits)
c = Counter(len(r["src"]) for r in solved)
print("source files changed per solved run:", sorted(c.items()))
