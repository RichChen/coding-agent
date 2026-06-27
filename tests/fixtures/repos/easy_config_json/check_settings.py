import json

with open("settings.json", encoding="utf-8") as f:
    data = json.load(f)

assert data["debug"] is False
assert data["port"] == 8080
assert data["service"] == "agent-demo"
print("settings ok")
