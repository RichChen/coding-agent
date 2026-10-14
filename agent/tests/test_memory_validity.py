import pytest

from reposkill_agent.memory.dependency_index import DependencyIndex
from reposkill_agent.memory.records import Dependency
from reposkill_agent.memory.validity import Fact, check_validity
from tests.upgrade_helpers import NOW, facts, validated


@pytest.mark.parametrize(
    ("kind", "expected", "actual", "status"),
    [
        ("api_signature", "(text)", "(text, strict)", "invalid"),
        ("api_signature", "(text)", "(text)", "valid"),
        ("package", ">=2,<3", "3.0", "invalid"),
        ("package", ">=2,<3", "2.8", "valid"),
        ("package", ">=2,<3", "unknown-version", "unknown"),
        ("file_hash", "old", "new", "unknown"),
    ],
)
def test_dependency_matrix(kind, expected, actual, status):
    r = validated(
        dependencies=(Dependency(kind=kind, key="api", expected=expected, evidence_ref="source"),)
    )
    f = facts(
        facts=(
            Fact(kind=kind, key="api", value=actual, evidence_ref="current", repo_revision="v1"),
        )
    )
    assert check_validity(r, f, NOW).status == status


def test_unrelated_revision_retains_and_same_revision_environment_invalidates():
    new_facts = facts(
        revision="v2",
        facts=(
            Fact(
                kind="api_signature",
                key="parse_config",
                value="(text)",
                evidence_ref="current",
                repo_revision="v2",
            ),
            Fact(
                kind="file_hash",
                key="unrelated.py",
                value="changed",
                evidence_ref="current",
                repo_revision="v2",
            ),
        ),
    )
    assert check_validity(validated(), new_facts, NOW).status == "valid"
    assert check_validity(validated(), facts(facts=()), NOW).status == "unknown"
    assert check_validity(validated(ttl_seconds=60), facts(), NOW).status == "unknown"
    assert (
        check_validity(validated(dependency_mapping_complete=False), facts(), NOW).status
        == "unknown"
    )
    assert check_validity(validated(), facts(repo_id="other"), NOW).status == "invalid"


def test_index_never_claims_unknown_is_unaffected():
    mapped = validated()
    unknown = validated(memory_id="unknown", dependency_mapping_complete=False)
    index = DependencyIndex([mapped, unknown])
    assert index.affected({("file_hash", "unrelated.py")}) == {"unknown"}
    assert index.affected({("api_signature", "parse_config")}) == {"memory-parser", "unknown"}


def test_stale_fact_and_conflicting_observations_unknown():
    old = Fact(
        kind="api_signature",
        key="parse_config",
        value="(text)",
        evidence_ref="e",
        repo_revision="v0",
    )
    assert check_validity(validated(), facts(facts=(old,)), NOW).status == "unknown"
    a = old.model_copy(update={"repo_revision": "v1"})
    b = a.model_copy(update={"value": "(x)"})
    assert check_validity(validated(), facts(facts=(a, b)), NOW).status == "unknown"
