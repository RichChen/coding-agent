from pathlib import Path

summary = Path("summary.md").read_text(encoding="utf-8")
assert "# Score Summary" in summary
assert "| Name | Score | Grade |" in summary
assert "Ada" in summary and "A" in summary
assert "Linus" in summary and "B" in summary
assert "Grace" in summary and "A" in summary
print("report ok")
