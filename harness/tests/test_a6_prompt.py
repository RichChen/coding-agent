import hashlib
import json
from pathlib import Path

import pytest
import yaml

from scripts.run_swe_task import ROOT, build_prompt, public_issue
from scripts.select_main_targets import PUBLIC_ROOT
from scripts.sprint5_prepare_main import FAMILY

# public_issue(task) for the dev tasks, computed before prompt_suffix existed.
DEV_PROMPT_SHA256 = {
    "django__django-10914": "e9d9f9ceb548ba4cc7e6f4700078aabae36cb4c0fb32568985bb5f82446e3e0a",
    "django__django-10924": "732f2369542f0e3a7750e810c2bc4c20fcc53f89927e42c1bfcc12b6d3fd68df",
    "django__django-11039": "2f2c40561cd215ee9f7cd4a5c3dacca9e5251cdda60396c8d95845878a3e5e3a",
    "pytest-dev__pytest-5103": "c2eee71050e28c69550d94eb698ac57328005090e112270471932f4a0a6a44f3",
    "pytest-dev__pytest-5227": "8e8cf079fce37656f825e1b37f1f750b257a4509cb65e2296924cee2b879c3d4",
    "sympy__sympy-11400": "dbd2fdd0ce700837d9e222045d02d86e53c8f2e23e3a17cdedecf11c578a2839",
    "sympy__sympy-11870": "7a542fa898be5aad9158b890b2e54e46fb01acc9213bb422edb887419cf0a9e2",
    "sympy__sympy-11897": "ba6c76521aa3f5c20c60c1f577af3f36f1b80eb33b0581b1671afa9d5055a112",
    "sympy__sympy-12171": "2c4cd634a311347153bd7b451d2d1e17f029ce3e2833f693ab259bf2bf0a1782",
    "scikit-learn__scikit-learn-10297": "ce80e052d0d5543da234231d2cb908ba40b01fcac9b3204cd98c46960af3a0d2",
    "scikit-learn__scikit-learn-10949": "e6fdd8718dd833408e9518fa929515f95fa81c7ca0e0281cbf494cf22c01fca6",
    "scikit-learn__scikit-learn-11281": "20304dcacb99bcd2a44ca6d42bf1a651571e49b4696d2239ae27c8db0ad6a65f",
    "scikit-learn__scikit-learn-10508": "4a9a3be2d4d1470ddf6545f6288bf0c68d88eda4eeb5cb984dea23d5bbd32f48",
    "scikit-learn__scikit-learn-11040": "236f9edb3f38819f95bf5854b45502f72d0da71d26d711f463bd513f9afdf4ca",
}


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _dev_tasks():
    tasks = yaml.safe_load((ROOT / "configs/sprint/dev-tasks.yaml").read_text(encoding="utf-8"))["tasks"]
    return [task for task in tasks if Path(task["public_task"]).is_file()]


def test_default_prompt_matches_the_dev_prompts_before_the_change():
    tasks = _dev_tasks()
    if not tasks:
        pytest.skip("dev public task files are not on disk")
    for task in tasks:
        assert _sha(build_prompt(task)) == DEV_PROMPT_SHA256[task["id"]]
        assert build_prompt(task, None) == build_prompt(task, "") == public_issue(task)


def test_suffix_follows_the_issue_after_one_blank_line():
    tasks = _dev_tasks()
    if not tasks:
        pytest.skip("dev public task files are not on disk")
    task = tasks[0]
    assert build_prompt(task, "<previous_attempt>\nx\n</previous_attempt>") == public_issue(task) + "\n\n<previous_attempt>\nx\n</previous_attempt>"


def test_default_prompt_matches_a5_b0_prompt_sha():
    root = ROOT / "runs" / "a5-main"
    summaries = sorted(root.glob("*/b0/r1/summary.json")) if root.is_dir() else []
    if not summaries:
        pytest.skip("A5 runs are not on disk")
    targets = {task["id"]: task for task in yaml.safe_load((ROOT / "configs/sprint/main-targets.yaml").read_text(encoding="utf-8"))["tasks"]}
    for path in summaries:
        summary = json.loads(path.read_text(encoding="utf-8"))
        target = targets[summary["task_id"]]
        task = {"public_task": str(PUBLIC_ROOT / (target["id"] + ".json")), "family": FAMILY[target["repo"]]}
        assert _sha(build_prompt(task)) == summary["prompt_sha256"], summary["task_id"]
