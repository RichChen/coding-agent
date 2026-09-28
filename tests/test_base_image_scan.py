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
