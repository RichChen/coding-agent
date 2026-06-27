from storage import load_user


def get_user_display(user_id):
    user = load_user(user_id)
    return user["name"]
