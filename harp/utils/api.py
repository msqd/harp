from packaging.version import Version


def api(version):
    def decorator(f):
        f.__api_version__ = Version(version)
        return f

    return decorator
