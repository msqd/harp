def ensure_bytes(x):
    if isinstance(x, bytes):
        return x
    return bytes(x, "utf-8")
