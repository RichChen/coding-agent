def parse_user(raw):
    name, email = raw.split("|")
    return {"name": name, "mail": email}
