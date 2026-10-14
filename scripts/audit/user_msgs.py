import json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
root = Path(r"C:\Users\Administrator\.cursor\projects\d-crq-src-coding-harness\agent-transcripts")
limit = int(sys.argv[2]) if len(sys.argv) > 2 else 300
for tid in sys.argv[1].split(","):
    f = root / tid / (tid + ".jsonl")
    if not f.exists():
        cands = list((root / tid).glob("*.jsonl")) if (root / tid).is_dir() else []
        if not cands:
            print("MISSING", tid)
            continue
        f = cands[0]
    print("=====", tid)
    for line in f.open(encoding="utf-8"):
        try:
            ev = json.loads(line)
        except Exception:
            continue
        if ev.get("role") != "user":
            continue
        msg = ev.get("message", {})
        content = msg.get("content") if isinstance(msg, dict) else msg
        if isinstance(content, list):
            text = " ".join(c.get("text", "") for c in content if isinstance(c, dict))
        else:
            text = str(content)
        if "<user_query>" in text:
            text = text.split("<user_query>", 1)[1].split("</user_query>", 1)[0]
        text = " ".join(text.split())
        print("-", text[:limit])
