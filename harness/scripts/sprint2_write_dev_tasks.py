import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
rows = {
    json.loads(line)["id"]: json.loads(line)
    for line in (ROOT / "runs/sprint2-calibrate/results.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip()
}
old = yaml.safe_load((ROOT / "configs/sprint/dev-tasks.yaml").read_text(encoding="utf-8"))
by_id = {task["id"]: task for task in old["tasks"]}
public_root = Path(r"D:\crq\src\coding-agent\reports\upgrade\a5-funded-build-preparation-20260921-v12\public")
extra = {
    "django__django-10914": ("django/django", "a5-build-b117be26241cbe45"),
    "django__django-10924": ("django/django", "a5-build-ae0fcdf9882e7432"),
    "django__django-11039": ("django/django", "a5-build-fc47f0f0fa3593e5"),
    "sympy__sympy-11897": ("sympy/sympy", "a5-build-9952d7b23356b0db"),
}
pick = [
    "django__django-10914", "django__django-10924", "django__django-11039",
    "pytest-dev__pytest-5103", "pytest-dev__pytest-5227",
    "sympy__sympy-11400", "sympy__sympy-11870", "sympy__sympy-11897", "sympy__sympy-12171",
    "scikit-learn__scikit-learn-10297", "scikit-learn__scikit-learn-10949", "scikit-learn__scikit-learn-11281",
]
tasks = []
for task_id in pick:
    row = rows[task_id]
    if task_id in by_id:
        repo = by_id[task_id]["repo"]
        public = by_id[task_id]["public_task"]
    else:
        repo, name = extra[task_id]
        public = str(public_root / f"{name}.json")
    if not Path(public).is_file():
        raise SystemExit("missing public " + task_id)
    tasks.append({
        "id": task_id,
        "repo": repo,
        "family": task_id.split("__", 1)[0],
        "receipt": row["receipt"] + "/receipt.json",
        "original": row["receipt"] + "/staging/original",
        "baseline": row["receipt"] + "/staging/baseline",
        "public_task": public,
        "grader_timeout_seconds": 600,
        "calibration": {
            "empty_f2p": row["empty_f2p"],
            "empty_p2p": row["empty_p2p"],
            "gold_f2p": row["gold_f2p"],
            "gold_p2p": row["gold_p2p"],
        },
        "p2p_excluded": row["p2p_excluded"],
    })
document = {
    "schema": "sprint.dev-tasks.v1",
    "variant": "B0",
    "notes": "Twelve tasks that passed empty-delta and gold-delta calibration.",
    "tasks": tasks,
}
(ROOT / "configs/sprint/dev-tasks.yaml").write_text(yaml.safe_dump(document, sort_keys=False, allow_unicode=True), encoding="utf-8")
print("wrote", len(tasks))
