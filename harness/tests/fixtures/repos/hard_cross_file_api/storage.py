USERS = {
    1: {"name": "Ada", "role": "admin"},
    2: {"name": "Linus", "role": "maintainer"},
}


def load_user(user_id):
    return USERS[user_id]
