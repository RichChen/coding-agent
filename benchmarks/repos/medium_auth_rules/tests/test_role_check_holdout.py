from auth_rules.api import check_role
from auth_rules.models import User


def test_admin_role_grants_editor_access():
    user = User(user_id="admin-1", name="Root", roles=["admin"])
    result = check_role(user, "editor")
    assert result.ok


def test_admin_role_grants_viewer_access():
    user = User(user_id="admin-2", name="Ops", roles=["admin"])
    result = check_role(user, "viewer")
    assert result.ok
