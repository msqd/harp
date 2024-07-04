from contextlib import contextmanager

from harp.settings import USE_PROMETHEUS

if USE_PROMETHEUS:
    from prometheus_client import Histogram

    _collectors = {}

    @contextmanager
    def performances_observer(name, /, *, labels=None):
        labels = labels or {}
        if name not in _collectors:
            _collectors[name] = Histogram(name, f"{name.title()} duration.", list(labels.keys()))

        with _collectors[name].labels(*labels.values()).time():
            yield

else:

    @contextmanager
    def performances_observer(name, /, *, labels=None):
        yield
