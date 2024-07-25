def truncate_string(s, max_length):
    if len(s) > max_length:
        return s[: max_length - 3] + "..."
    return s
