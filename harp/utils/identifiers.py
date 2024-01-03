def is_valid_dotted_identifier(name):
    return all(s and s.isidentifier() for s in name.split("."))
