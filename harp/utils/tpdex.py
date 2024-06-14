from math import log, sqrt


def _tpdex(n):
    # This formula looks like a mess, but we spent quite some time for tuning it. Please do not change this unless
    # you are aware of the previous work and the impact it has.
    if n < 1328:
        return min(1 - 7.22e-4 * n + 2.44e-7 * (n**2) - 3e-11 * (n**3), 1)
    return max(-0.42115982438869104 * log(sqrt(n) + 1) + 1.9270515661020815, 0)


def tpdex(n):
    return int(_tpdex(n) * 100)
