import tomllib


def load(filename):
    with open(filename, "rb") as f:
        return tomllib.load(f)
