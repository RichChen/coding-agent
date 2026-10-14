import ast, base64, json, sys
from pathlib import Path
import yaml

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"D:\crq\src\coding-harness")
runs = ROOT / "runs/sprint2-b0"
for t in ["scikit-learn__scikit-learn-10297", "scikit-learn__scikit-learn-10949", "scikit-learn__scikit-learn-11281"]:
    delta = json.loads((runs / t / "candidate-delta.json").read_text(encoding="utf-8"))
    for name, enc in delta["changed"].items():
        src = base64.b64decode(enc)
        try:
            ast.parse(src)
            ok = "parses"
        except SyntaxError as exc:
            ok = f"SyntaxError line {exc.lineno}: {exc.msg}"
        print(t, name, len(src), ok)

m = yaml.safe_load((ROOT / "configs/sprint/dev-tasks.yaml").read_text(encoding="utf-8"))
for task in m["tasks"]:
    print(task["id"], "grader_timeout", task.get("grader_timeout_seconds"), "p2p_excluded", len(task.get("p2p_excluded") or []))
cal = ROOT / "runs/sprint2-calibrate/results.jsonl"
if cal.exists():
    for line in cal.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        if "scikit" in r["id"]:
            print("calib", r["id"], r["accepted"], r["gold_f2p"], r["gold_p2p"], r["empty_p2p"], r["empty_p2p_total"])

prof = yaml.safe_load((ROOT / "configs/sprint/b0.yaml").read_text(encoding="utf-8"))
print("runtime:", json.dumps(prof.get("runtime"), ensure_ascii=False))
print("tools:", json.dumps(prof.get("tools"), ensure_ascii=False)[:600])
