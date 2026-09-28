from scripts.sprint5_prepare_main import django_selection, django_test_module, grade_verdict

SEARCH = '''
from django.test import TestCase


class SearchTests(TestCase):
    def test_multi_valued(self):
        """
        Searches over multi-valued relationships return rows from related
        models only once.
        """

    def test_plain(self):
        pass

    def test_first(self):
        """Shared first line."""

    def test_second(self):
        """Shared first line.

        Different body.
        """
'''

OTHER = '''
import unittest


class OtherTests(unittest.TestCase):
    def test_located(self):
        pass

    def test_documented(self):
        """Only found through a module another id points at."""

    def helper(self):
        """Not a test, never matched."""
'''


def _tree(tmp_path):
    (tmp_path / "tests" / "admin_changelist").mkdir(parents=True)
    (tmp_path / "tests" / "admin_changelist" / "tests.py").write_text(SEARCH, encoding="utf-8")
    (tmp_path / "tests" / "other").mkdir(parents=True)
    (tmp_path / "tests" / "other" / "tests.py").write_text(OTHER, encoding="utf-8")
    return tmp_path


def test_module_name_is_relative_to_tests():
    assert django_test_module("tests/admin_changelist/tests.py") == "admin_changelist.tests"
    assert django_test_module("tests/app/__init__.py") == "app"
    assert django_test_module("django/db/models.py") is None


def test_docstring_ids_map_to_their_test_method(tmp_path):
    root = _tree(tmp_path)
    raw = {
        "f2p": ["Searches over multi-valued relationships return rows from related"],
        "p2p": [
            "test_plain (admin_changelist.tests.SearchTests)",
            "test_located (other.tests.OtherTests)",
            "Only found through a module another id points at.",
            "Shared first line.",
            "Not a test, never matched.",
        ],
    }
    selected, dropped, mapping = django_selection(raw, root, ["tests/admin_changelist/tests.py"])
    assert selected["f2p"] == ["admin_changelist.tests.SearchTests.test_multi_valued"]
    assert selected["p2p"] == [
        "admin_changelist.tests.SearchTests.test_plain",
        "other.tests.OtherTests.test_located",
        "other.tests.OtherTests.test_documented",
    ]
    assert [(item["side"], item["nodeid"]) for item in mapping] == [
        ("f2p", "admin_changelist.tests.SearchTests.test_multi_valued"),
        ("p2p", "other.tests.OtherTests.test_documented"),
    ]
    reasons = {item["nodeid"]: item["reason"] for item in dropped}
    assert reasons == {
        "Shared first line.": "docstring_ambiguous",
        "Not a test, never matched.": "docstring_unmatched",
    }


def test_docstring_outside_the_scanned_files_is_not_mapped(tmp_path):
    root = _tree(tmp_path)
    raw = {"f2p": ["Only found through a module another id points at."], "p2p": []}
    selected, dropped, _ = django_selection(raw, root, ["tests/admin_changelist/tests.py"])
    assert selected["f2p"] == []
    assert dropped[0]["reason"] == "docstring_unmatched"


def test_an_unaddressable_f2p_excludes_the_task():
    row = {
        "empty_f2p": [0, 1],
        "gold_f2p": [1, 1],
        "nodeids": {"dropped": [{"side": "f2p", "nodeid": "x", "reason": "docstring_unmatched"}]},
    }
    assert grade_verdict(row) == (False, "f2p_unaddressable")
    row["nodeids"]["dropped"][0]["side"] = "p2p"
    assert grade_verdict(row) == (True, None)
