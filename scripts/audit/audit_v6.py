import hashlib, json, re, sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
H = Path(r"D:\crq\src\coding-harness")
A = Path(r"D:\crq\src\coding-agent")
sys.path.insert(0, str(A))
from reposkill_agent.memory.cards import load_memory_cards, render_card  # noqa: E402

mode = sys.argv[1] if len(sys.argv) > 1 else "all"
cards_path = A / "benchmarks/a5/memory-cards-v6.jsonl"
cards = load_memory_cards(cards_path)
manifest = json.loads((A / "benchmarks/a5/memory-cards-v6.manifest.json").read_text(encoding="utf-8"))
by_id = {c.source_id: c for c in cards}

if mode == "show":
    for sid in sys.argv[2:]:
        print("=" * 30, sid)
        print(render_card(by_id[sid]))
    sys.exit()

# 1. manifest hashes
print("cards:", len(cards), "manifest status:", manifest["status"])
print("cards_sha256 ok:", hashlib.sha256(cards_path.read_bytes()).hexdigest() == manifest["cards_sha256"])
lf = lambda p: hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
for h in manifest["build_inputs"]["handoffs"]:
    print("handoff", h["schema"], h["sha256"][:12])
print("dev handoff now:", lf(H / "docs/sprint/memory-source-runs.json")[:12], "pool handoff now:", lf(H / "docs/sprint/main-b0-runs.json")[:12])

# 2. labels vs handoffs
runs = defaultdict(list)
for doc in ("memory-source-runs.json", "main-b0-runs.json"):
    for r in json.loads((H / "docs/sprint" / doc).read_text(encoding="utf-8"))["runs"]:
        runs[r["source_id"]].append(r)
bad = []
for c in cards:
    rs = runs[c.source_id]
    solved = sorted(int(r["repeat"]) for r in rs if r.get("solved"))
    want_status = "validated_fix" if solved else "failed_attempt"
    want_run = f"r{solved[0]}" if solved else "r" + str(min(int(r["repeat"]) for r in rs if r.get("status") != "infra_error"))
    got_run = c.source_run.split(" ", 1)[0]
    meta = rs[0]
    if c.verification_status != want_status or got_run != want_run or c.repo != meta["repo"] or c.created_at != meta["created_at"]:
        bad.append((c.source_id, c.verification_status, want_status, got_run, want_run, c.repo, c.created_at, meta["created_at"]))
print("label/run/repo/date mismatches:", bad)
print("sources in handoffs without card:", sorted(set(runs) - set(by_id)))

# 3. rendered sizes + field emptiness
sizes = [len(render_card(c).encode("utf-8")) for c in cards]
print("rendered bytes min/median/max:", min(sizes), sorted(sizes)[len(sizes) // 2], max(sizes))
empty = Counter()
for c in cards:
    for f in ("issue_summary", "relevant_files", "fix_approach", "test_commands"):
        if not getattr(c, f):
            empty[(c.verification_status, f)] += 1
print("empty fields:", dict(empty))

# 4. private leakage: source's own gold/test patch added lines, and F2P/P2P ids, in the rendered card
def added(patch):
    return {l[1:].strip() for l in (patch or "").splitlines() if l.startswith("+") and not l.startswith("+++") and len(l[1:].strip()) >= 25}

leak = []
for c in cards:
    p = H / "runs/sprint5-main-private" / (c.source_id + ".json")
    if not p.is_file():
        continue
    priv = json.loads(p.read_text(encoding="utf-8"))
    text = render_card(c) + "\n" + json.dumps(c.model_dump(mode="json"), ensure_ascii=False)
    tp = [l for l in added(priv.get("test_patch")) if l in text]
    gp = [l for l in added(priv.get("patch")) if l in text]
    ids = json.loads(priv["FAIL_TO_PASS"]) + json.loads(priv["PASS_TO_PASS"])
    idhits = [i for i in ids if len(i) > 12 and i in text]
    if tp or idhits:
        leak.append((c.source_id, len(tp), len(idhits)))
        if mode == "detail":
            f2p = set(json.loads(priv["FAIL_TO_PASS"]))
            for l in tp:
                fields = [f for f, v in c.model_dump(mode="json").items() if l in json.dumps(v, ensure_ascii=False)]
                print("   TESTLINE", c.source_id, repr(l[:120]), "fields:", fields)
            for i in idhits:
                print("   ID", c.source_id, "F2P" if i in f2p else "P2P", repr(i[:120]))
    if gp:
        leak.append((c.source_id, "own-gold-lines", len(gp)))
print("source-private content in cards (test lines, ids) / own gold lines:", leak)
