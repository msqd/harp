def ensure_bytes(x):
    if isinstance(x, bytes):
        return x
    return bytes(x, "utf-8")


def ensure_str(x):
    if isinstance(x, str):
        return x
    return str(x, "utf-8")
