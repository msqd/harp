import os


def cast_bool(x):
    if isinstance(x, str):
        value = x.lower()
        if value in ("true", "yes", "1"):
            return True
        elif value in ("false", "no", "0"):
            return False
        else:
            raise ValueError(f"Invalid string value: {x}")
    return bool(x)


def get_bool_from_env(key, default):
    value = os.environ.get(key, None)

    if value is None:
        return default

    try:
        return cast_bool(value)
    except ValueError:
        raise ValueError(f"Invalid boolean value for {key}: {value!r}")
