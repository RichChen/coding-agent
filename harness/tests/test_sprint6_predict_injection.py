import json

from scripts import sprint6_predict_injection as predict


def test_gold_overlap_counts_added_lines_found_in_card_text(tmp_path, monkeypatch):
    monkeypatch.setattr(predict, "ROOT", tmp_path)
    patch = "--- a/x.py\n+++ b/x.py\n@@\n-old = 1\n+    value = compute(table_name)\n+x\n+\n context\n"
    (tmp_path / "p.json").write_text(json.dumps({"patch": patch}), encoding="utf-8")
    task = {"private": "p.json"}
    counts = predict.gold_overlap(task, ["approach: call\nvalue = compute(table_name)\nx"])
    assert counts == {
        "gold_added_lines": 2,
        "in_injected_text": 2,
        "gold_added_lines_nontrivial": 1,
        "in_injected_text_nontrivial": 1,
    }
    assert predict.gold_overlap(task, [])["in_injected_text"] == 0


def test_audit_flags_later_own_and_cross_repo_cards():
    cards = {
        "a": {"repo": "r/r", "created_at": "2019-01-01T00:00:00Z"},
        "b": {"repo": "r/r", "created_at": "2021-01-01T00:00:00Z"},
        "c": {"repo": "o/o", "created_at": "2019-01-01T00:00:00Z"},
        "t": {"repo": "r/r", "created_at": "2020-01-01T00:00:00Z"},
    }
    row = {"id": "t", "repo": "r/r", "created_at": "2020-01-01T00:00:00Z", "injected": [{"id": key} for key in "abct"]}
    found = predict.audit([row], cards)
    assert found == {"later_than_target": ["t <- b", "t <- t"], "own_task": ["t"], "cross_repo": ["t <- c"]}
    row["injected"] = [{"id": "a"}]
    assert predict.audit([row], cards) == {"later_than_target": [], "own_task": [], "cross_repo": []}
