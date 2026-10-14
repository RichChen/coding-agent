from scripts.build_clean_baseline import exclude_base_image_matches


def test_same_hash_as_the_base_image_is_not_a_hit():
    found = [
        {"path": "/usr/local/lib/python3.9/pickle.py", "sha256": "abc"},
        {"path": "/opt/repo/django/db/models.py", "sha256": "def"},
        {"path": "/usr/local/lib/python3.9/site-packages/babel/messages/mofile.py", "sha256": "fff"},
    ]
    base = {
        "/usr/local/lib/python3.9/pickle.py": "abc",
        "/opt/repo/django/db/models.py": None,
        "/usr/local/lib/python3.9/site-packages/babel/messages/mofile.py": None,
    }
    hits, same = exclude_base_image_matches(found, base)
    assert [item["path"] for item in hits] == [
        "/opt/repo/django/db/models.py",
        "/usr/local/lib/python3.9/site-packages/babel/messages/mofile.py",
    ]
    assert same == ["/usr/local/lib/python3.9/pickle.py"]


def test_unmodified_pip_record_is_not_a_hit():
    from scripts.build_clean_baseline import exclude_recorded_installs

    found = [
        {"path": "/usr/local/lib/python3.9/site-packages/babel/messages/mofile.py", "sha256": "fff"},
        {"path": "/opt/repo/sphinx/application.py", "sha256": "gold"},
    ]
    hits, same = exclude_recorded_installs(found, {"fff"})
    assert hits == ["/opt/repo/sphinx/application.py"]
    assert same == ["/usr/local/lib/python3.9/site-packages/babel/messages/mofile.py"]


def test_repo_packages_are_top_level_dirs_with_init():
    from scripts.build_clean_baseline import repo_packages

    manifest = {"entries": {
        "sphinx/__init__.py": {}, "sphinx/util/__init__.py": {}, "tests/conftest.py": {},
        "src/_pytest/__init__.py": {}, "setup.py": {},
    }}
    assert repo_packages(manifest) == {"sphinx", "_pytest"}


def test_opt_repo_and_project_package_hits_are_never_excused():
    from scripts.build_clean_baseline import exclude_recorded_installs, exclusion_guarded

    packages = {"sphinx"}
    found = [
        {"path": "/opt/repo/setup.py", "sha256": "same"},
        {"path": "/usr/local/lib/python3.9/site-packages/sphinx/application.py", "sha256": "same"},
        {"path": "/root/.cache/pip/wheels/x.zip!sphinx/builders/html.py", "sha256": "same"},
        {"path": "/usr/local/lib/python3.9/site-packages/babel/messages/mofile.py", "sha256": "same"},
    ]
    base = {item["path"]: "same" for item in found}
    hits, same = exclude_base_image_matches(found, base, packages)
    assert [item["path"] for item in hits] == [item["path"] for item in found[:3]]
    assert same == ["/usr/local/lib/python3.9/site-packages/babel/messages/mofile.py"]
    hits, same = exclude_recorded_installs(found, {"same"}, packages)
    assert hits == sorted(item["path"] for item in found[:3])
    assert same == ["/usr/local/lib/python3.9/site-packages/babel/messages/mofile.py"]
    assert not exclusion_guarded("/usr/local/lib/python3.9/site-packages/sphinxcontrib/x.py", packages)
