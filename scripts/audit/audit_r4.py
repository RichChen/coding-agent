import json, sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"D:\crq\src\coding-harness")
runs = ROOT / "runs/sprint4-b0-v2"
print("exists", runs.exists())
for task_dir in sorted(p for p in runs.iterdir() if p.is_dir()):
    for r in sorted(p for p in task_dir.iterdir() if p.is_dir()):
        s = json.loads((r / "summary.json").read_text(encoding="utf-8")) if (r / "summary.json").exists() else {}
        g = json.loads((r / "grader-result.json").read_text(encoding="utf-8")) if (r / "grader-result.json").exists() else {}
        cases = Counter(c.get("outcome") for c in g.get("cases") or [])
        iso = s.get("answer_isolation") or {}
        print(f"{task_dir.name[-22:]:>22} {r.name} solved={s.get('solved')} st={s.get('status')} f2p={g.get('f2p_passed')}/{g.get('f2p_total')} "
              f"p2p={g.get('p2p_passed')}/{g.get('p2p_total')} cases={dict(cases)} collected={g.get('collected')} "
              f"calls={s.get('model_calls')} cost={s.get('cost_cny')} files={s.get('changed_files')} iso={iso.get('pass', s.get('answer_isolation_pass'))} "
              f"err={str(g.get('reason') or g.get('runner_error') or '')[:60]}")
