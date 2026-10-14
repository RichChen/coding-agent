import base64, difflib, json, re, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
H = Path(r"D:\crq\src\coding-harness")
task, path = sys.argv[1], sys.argv[2]
orig = (H / "runs/sprint5-main-images" / task / "staging/original" / path).read_text(encoding="utf-8").splitlines()


def funcs_changed(new_lines):
    changed = set()
    sm = difflib.SequenceMatcher(a=orig, b=new_lines, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        for i in range(min(i1, len(orig) - 1), -1, -1):
            m = re.match(r"\s*def (\w+)", orig[i])
            if m:
                changed.add(m.group(1))
                break
    return sorted(changed)


priv = json.loads((H / "runs/sprint5-main-private" / (task + ".json")).read_text(encoding="utf-8"))
gold_hunks = re.findall(r"^@@.*@@\s*(.*)$", priv["patch"], re.M)
print("gold hunk contexts:", gold_hunks)
for phase in ("b0", "b2"):
    for k in (1, 2, 3):
        d = H / "runs/a5-main" / task / phase / f"r{k}"
        delta = json.loads((d / "candidate-delta.json").read_text(encoding="utf-8"))
        s = json.loads((d / "summary.json").read_text(encoding="utf-8")).get("solved")
        blob = (delta.get("changed") or {}).get(path)
        if blob is None:
            print(phase, k, "solved", s, "file unchanged")
            continue
        new = base64.b64decode(blob).decode("utf-8").splitlines()
        added = sum(1 for l in difflib.unified_diff(orig, new, lineterm="") if l.startswith("+") and not l.startswith("+++"))
        print(phase, k, "solved", s, "functions changed:", funcs_changed(new), "added lines:", added)
