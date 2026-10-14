from parser import parse_user


def describe(raw):
    user = parse_user(raw)
    return f"{user['name']} <{user['email']}>"
