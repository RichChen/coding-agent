import json, sys, re
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")


def load(path):
    rows = [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]
    states = [r for r in rows if r["event_type"] == "state.saved" and "messages" in (r.get("payload") or {})]
    msgs = states[-1]["payload"]["messages"]
    tools = set()
    for m in msgs:
        for tc in m.get("tool_calls") or []:
            tools.add((tc.get("function") or tc).get("name"))
    started = next(r for r in rows if r["event_type"] == "run.started")["payload"]
    return msgs, tools, started


dev_msgs, dev_tools, dev_start = load(sys.argv[1])
pool_msgs, pool_tools, pool_start = load(sys.argv[2])
print("system prompt identical:", dev_msgs[0]["content"] == pool_msgs[0]["content"])
strip = lambda s: re.sub(r"(Repository|Base revision): .*", "", s.split("Public issue:")[0])
print("user template identical (before issue):", strip(dev_msgs[1]["content"]) == strip(pool_msgs[1]["content"]))
print("dev issue chars:", len(dev_msgs[1]["content"].split("Public issue:")[1]))
print("pool issue chars:", len(pool_msgs[1]["content"].split("Public issue:")[1]))
print("tools used dev:", sorted(dev_tools))
print("tools used pool:", sorted(pool_tools))
for key in ("backend", "budget", "profile", "model", "llm", "config"):
    if key in dev_start or key in pool_start:
        a, b = dev_start.get(key), pool_start.get(key)
        if a != b:
            print("run.started diff", key)
            print("  dev :", json.dumps(a, ensure_ascii=False)[:400])
            print("  pool:", json.dumps(b, ensure_ascii=False)[:400])
print("run.started keys:", sorted(pool_start.keys()))
