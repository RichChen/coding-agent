"""Post-hoc, read-only: anchoring breakdown for A6-R. Not preregistered."""
import collections, difflib, json, sys
from pathlib import Path

H = Path(r"D:\crq\src\coding-harness")
sys.path.insert(0, r"D:\crq\src\coding-agent")
from scripts.a6_diff import diff_against, load_delta  # noqa: E402

runs = json.loads((H / "docs/sprint/a6-retry-runs.json").read_text(encoding="utf-8"))["runs"]
recs = json.loads((H / "docs/sprint/a6-attempts.json").read_text(encoding="utf-8"))["records"]
first_dir = {(r["task"], r["first"]): r["run_dir"] for r in recs}

def diff_of(task, run_dir):
    p = Path(run_dir)
    p = p if p.is_absolute() else H / p
    d = load_delta(p)
    return diff_against(d, H / "runs/sprint5-main-images" / task / "staging/original") if d else ""

first = {k: diff_of(k[0], v) for k, v in first_dir.items()}
rows = []
for x in runs:
    k = (x["task_id"], x["first"])
    sec = diff_of(x["task_id"], x["run_dir"])
    f = first[k]
    rows.append(dict(arm=x["arm"], task=k[0], first=k[1], solved=bool(x["solved"]),
                     f_empty=not f.strip(), s_empty=not sec.strip(), same=(sec == f),
                     sim=difflib.SequenceMatcher(None, f, sec).ratio() if f and sec else None))

out = collections.defaultdict(lambda: collections.Counter())
for r in rows:
    c = out[r["arm"]]
    c["n"] += 1
    c["same"] += r["same"]
    c["same_both_empty"] += r["same"] and r["f_empty"]
    c["same_nonempty"] += r["same"] and not r["f_empty"]
    c["first_nonempty"] += not r["f_empty"]
    if r["sim"] is not None:
        c["sim_n"] += 1
        c["sim_ge_0.9"] += r["sim"] >= 0.9
        c["sim_ge_0.9_solved"] += r["sim"] >= 0.9 and r["solved"]
        c["sim_lt_0.9_solved"] += r["sim"] < 0.9 and r["solved"]
        c["sim_lt_0.9"] += r["sim"] < 0.9
for arm in ("r0", "r1"):
    print(arm, dict(out[arm]))
for arm in ("r0", "r1"):
    sims = sorted(r["sim"] for r in rows if r["arm"] == arm and r["sim"] is not None)
    q = lambda p: round(sims[int(p * (len(sims) - 1))], 3)
    print(arm, "sim quartiles", q(.25), q(.5), q(.75), "n", len(sims))
