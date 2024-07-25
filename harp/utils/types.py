def typeof(x, *, short=False):
    x = type(x)
    if short:
        return f"{x.__qualname__}"
    return f"{x.__module__}.{x.__qualname__}"
