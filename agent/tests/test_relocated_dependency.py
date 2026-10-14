from reposkill_agent.memory.records import CardDependency
from reposkill_agent.memory.validity import check_card_dependencies


def test_missing_path_with_symbol_elsewhere_is_relocated(tmp_path):
    package = tmp_path / "pkg"
    package.mkdir()
    (package / "moved.py").write_text("def fit_predict(self):\n    return []\n", encoding="utf-8")
    result = check_card_dependencies(
        (CardDependency(path="old/base.py", symbols=("fit_predict",)),),
        tmp_path,
    )
    assert result.status == "unknown"
    assert result.checks[0].reason.startswith("relocated:")


def test_missing_path_and_missing_symbol_stays_invalid(tmp_path):
    result = check_card_dependencies(
        (CardDependency(path="old/base.py", symbols=("fit_predict",)),),
        tmp_path,
    )
    assert result.status == "invalid"
    assert result.checks[0].reason.startswith("dependency_path_missing:")
