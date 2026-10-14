import json, re, sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
H = Path(r"D:\crq\src\coding-harness")
A = Path(r"D:\crq\src\coding-agent")
sys.path.insert(0, str(A))
from reposkill_agent.memory.cards import load_memory_cards  # noqa: E402

cards = {c.source_id: c for c in load_memory_cards(A / "benchmarks/a5/memory-cards-v6.jsonl")}
pred = {r["id"]: r for r in json.loads((H / "docs/sprint/b2-predicted-injection.json").read_text(encoding="utf-8"))["runs"]}


def gold_files(task):
    priv = json.loads((H / "runs/sprint5-main-private" / (task + ".json")).read_text(encoding="utf-8"))
    return set(re.findall(r"^\+\+\+ b/(\S+)", priv["patch"], re.M))


def card_files(card):
    files = {f.split(":", 1)[0] for f in card.relevant_files}
    files |= {d.path for d in card.dependencies}
    return {f for f in files if not re.search(r"(^|/)tests?/|test_", f)}


def solved_list(task, phase):
    out = []
    for k in (1, 2, 3):
        p = H / "runs/a5-main" / task / phase / f"r{k}" / "summary.json"
        if p.is_file():
            out.append(bool(json.loads(p.read_text(encoding="utf-8")).get("solved")))
    return out


def run_files(task, phase, k):
    """Files the agent opened/edited (from tool.intent payloads) and final delta files."""
    d = H / "runs/a5-main" / task / phase / f"r{k}"
    touched = []
    ev = d / "events.jsonl"
    if ev.is_file():
        for line in ev.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if r["event_type"] != "tool.intent":
                continue
            s = json.dumps(r.get("payload"), ensure_ascii=False)
            for m in re.findall(r'"path": "([^"]+)"', s):
                m = m.removeprefix("/workspace/").lstrip("./")
                if m and m not in touched:
                    touched.append(m)
    delta = json.loads((d / "candidate-delta.json").read_text(encoding="utf-8")) if (d / "candidate-delta.json").is_file() else {}
    edited = {p for p in (delta.get("changed") or {}) if not re.search(r"(^|/)tests?/|test_", p)}
    return touched, edited


mode = sys.argv[1] if len(sys.argv) > 1 else "table"
rows = []
for task, r in pred.items():
    inj = [i["id"] for i in r["injected"]]
    g = gold_files(task)
    cf = set().union(*[card_files(cards[i]) for i in inj]) if inj else set()
    b0, b2 = solved_list(task, "b0"), solved_list(task, "b2")
    d = (sum(b2) / len(b2) if b2 else 0) - (sum(b0) / len(b0) if b0 else 0)
    rows.append(dict(task=task, inj=inj, gold=g, cardfiles=cf, hit=bool(g & cf), b0=sum(b0), b2=sum(b2), d=d))

if mode == "table":
    inj = [x for x in rows if x["inj"]]
    hit = [x for x in inj if x["hit"]]
    miss = [x for x in inj if not x["hit"]]
    avg = lambda xs: sum(x["d"] for x in xs) / len(xs) if xs else float("nan")
    print(f"injected tasks {len(inj)}; card files overlap gold files: {len(hit)}; no overlap: {len(miss)}")
    print(f"mean d  overlap={avg(hit):+.3f} (n={len(hit)})  no-overlap={avg(miss):+.3f} (n={len(miss)})  not-injected={avg([x for x in rows if not x['inj']]):+.3f}")
    print("\noverlap tasks:")
    for x in hit:
        print(f"  {x['task']:<34} B0 {x['b0']}/3 B2 {x['b2']}/3  shared={sorted(x['gold'] & x['cardfiles'])}  cards={x['inj']}")
    print("\nchanged tasks (d != 0):")
    for x in sorted(rows, key=lambda x: x["d"]):
        if x["d"]:
            print(f"  {x['task']:<34} d={x['d']:+.2f} B0 {x['b0']}/3 B2 {x['b2']}/3 overlap={x['hit']} cards={x['inj']}")
elif mode == "follow":
    # Did B2 agents open card-only files (in card, not in gold)? Did the final edit land on them?
    opened_card_only = edited_card_only = total = 0
    per = []
    for x in rows:
        if not x["inj"]:
            continue
        decoy = x["cardfiles"] - x["gold"]
        for k in (1, 2, 3):
            touched, edited = run_files(x["task"], "b2", k)
            if not touched and not edited:
                continue
            total += 1
            b0_touched = set()
            for kk in (1, 2, 3):
                b0_touched |= set(run_files(x["task"], "b0", kk)[0])
            oc = decoy & set(touched) - b0_touched
            ec = decoy & edited
            opened_card_only += bool(oc)
            edited_card_only += bool(ec)
            if oc or ec:
                per.append((x["task"], k, sorted(oc)[:3], sorted(ec)))
    print(f"B2 runs: {total}; opened a card-suggested non-gold file never opened in any B0 run: {opened_card_only}; final edit on such a file: {edited_card_only}")
    for p in per[:25]:
        print("  ", p)
elif mode == "task":
    t = sys.argv[2]
    x = next(r for r in rows if r["task"] == t)
    print("gold:", sorted(x["gold"]))
    for i in x["inj"]:
        print("card", i, "files:", sorted(card_files(cards[i])))
        print("   approach:", cards[i].fix_approach[:300])
    for phase in ("b0", "b2"):
        for k in (1, 2, 3):
            touched, edited = run_files(t, phase, k)
            s = solved_list(t, phase)
            print(f"{phase} r{k} solved={s[k-1] if len(s) >= k else None} edited={sorted(edited)} first-opened={touched[:8]}")
