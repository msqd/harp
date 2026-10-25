"""Slowing down who guesses passwords.

Failed sign-ins are counted per account name and per address. From the fifth failure on, the next attempt has to wait,
twice as long each time, up to :data:`MAX_DELAY`: never a lockout, so that nobody can be shut out for good by someone
typing their name. An attempt made too early is refused without looking at the password, so guessing during the wait
brings nothing.

Counts are per process and in memory: with several workers, an attacker gets as many guesses as there are workers. They
are forgotten after :data:`FORGET_AFTER` seconds without failure, and bounded in number.
"""

from collections import OrderedDict
from time import monotonic
from typing import Callable

#: Failures that cost nothing: a person mistypes.
FREE_FAILURES = 5

#: The longest wait, in seconds.
MAX_DELAY = 300.0

#: A key without failure for this long (seconds) starts again from zero.
FORGET_AFTER = 900.0

MAX_ENTRIES = 10_000


def _delay(failures: int) -> float:
    if failures < FREE_FAILURES:
        return 0.0
    return min(2.0 ** min(failures - FREE_FAILURES, 32), MAX_DELAY)


class SignInThrottle:
    def __init__(self, *, clock: Callable[[], float] = monotonic, max_entries: int = MAX_ENTRIES):
        self.clock = clock
        self.max_entries = max_entries
        # key -> (failures, time of the last one), least recently failed first
        self._failures: OrderedDict[tuple[str, str], tuple[int, float]] = OrderedDict()

    def __len__(self):
        return len(self._failures)

    def _remaining(self, key: tuple[str, str]) -> float:
        entry = self._failures.get(key)
        if entry is None:
            return 0.0
        failures, last = entry
        elapsed = self.clock() - last
        if elapsed >= FORGET_AFTER:
            del self._failures[key]
            return 0.0
        return max(0.0, _delay(failures) - elapsed)

    def retry_after(self, username: str, ip: str) -> float:
        """Seconds to wait before the next attempt of this account from this address, 0 when it may go."""
        return max(self._remaining(("account", username)), self._remaining(("ip", ip)))

    def failed(self, username: str, ip: str) -> None:
        """
        Counts a failure. It is called when an attempt starts, before the password is looked at, and taken back by
        :meth:`succeeded`: a guess that has not been answered yet already counts, so that a thousand guesses sent at once
        meet the wait as the sixth does, instead of all passing the check before the first failure is recorded.
        """
        for key in (("account", username), ("ip", ip)):
            self._remaining(key)  # forgets what is old
            failures = self._failures.pop(key, (0, 0.0))[0] + 1
            self._failures[key] = (failures, self.clock())
        while len(self._failures) > self.max_entries:
            self._failures.popitem(last=False)

    def succeeded(self, username: str, ip: str) -> None:
        """
        The account proved itself: its failures are forgotten. The attempt was counted as a failure before it was
        known (see :meth:`failed`), the address gets that one back, and keeps the others: an attacker owning one valid
        account must not wash its guesses against the others.
        """
        self._failures.pop(("account", username), None)
        entry = self._failures.get(("ip", ip))
        if entry is not None:
            failures, last = entry
            if failures <= 1:
                del self._failures[("ip", ip)]
            else:
                self._failures[("ip", ip)] = (failures - 1, last)
