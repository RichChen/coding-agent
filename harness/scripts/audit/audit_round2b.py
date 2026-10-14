import json, re, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"D:\crq\src\coding-harness\runs\sprint2-b0")

g = json.loads((ROOT / "scikit-learn__scikit-learn-10297" / "grader-result.json").read_text(encoding="utf-8"))
print("grader keys:", list(g.keys()))
text = json.dumps(g, ensure_ascii=False)
for pat in [r"\.so", "ImportError", "ModuleNotFoundError", "undefined symbol", "cannot import", "Error"]:
    m = [x.start() for x in re.finditer(pat, text)][:3]
    for i in m:
        print(f"[{pat}]", text[max(0, i - 200): i + 200].replace("\\n", " | "))
        print("---")

rows = [json.loads(l) for l in (ROOT / "sympy__sympy-11870" / "events.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
print("\n== 11870 tool.result samples")
n = 0
for r in rows:
    if r.get("event_type") == "tool.result":
        p = r.get("payload") or {}
        s = json.dumps(p, ensure_ascii=False)
        if "edit" in s[:400] or "fu.py" in s[:600]:
            print(s[:500]); print("---"); n += 1
        if n >= 3:
            break
fin = [r for r in rows if r.get("event_type") == "run.finished"]
print("\n== run.finished:", json.dumps(fin[-1], ensure_ascii=False)[:600] if fin else None)
print("\n== last events types:", [r.get("event_type") for r in rows[-8:]])
