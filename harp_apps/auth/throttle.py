"""Slowing down who guesses passwords, without letting anyone slow down somebody else.

Every limit *refuses*: an attempt over a limit is answered ``429`` with ``Retry-After``, before its password is looked at
and without holding anything on the server, so the limits cap how many guesses get through and a flood cannot starve
the others by queueing. Three counts, each with its own consequence:

* **one address against one account** (the pair): from the fifth failure, that address waits 1 s, 2 s, 4 s ... up to
  :data:`MAX_WAIT` before its next attempt on that account. Another address is another pair.
* **one account, every address**: after 100 consecutive failures (NIST SP 800-63B-4), addresses that never signed in to
  the account wait the same way. The last :data:`KNOWN_ADDRESSES` addresses that did are exempt.
* **one address, every account** (IPv6 by /64): after :data:`ADDRESS_FREE_FAILURES` failures it waits the same way. This
  is what stops an address that piles up penalised pairs, and it takes over for a pair or an account the table has no
  room to record. Cost accepted: behind a reverse proxy HARP does not know (see ``dashboard.trusted_proxies``), the
  neighbours of an attacker get short refusals.

Only failures that completed are counted, so parallel valid requests (a dashboard fetching six things at once) are never
refused for being parallel; the number of attempts of one pair under way at once is bounded instead
(:data:`PAIR_FREE_FAILURES` + :data:`IN_FLIGHT_SLACK`), and the hashing queue bounds the rest.

Entries still under penalty are never evicted to make room: a flood of fresh names leaves the waits where they are. Counts
are per process and in memory: with several workers an attacker gets as many guesses as there are workers.
"""

import ipaddress
from collections import OrderedDict
from dataclasses import dataclass
from time import monotonic
from typing import Callable

#: Failures of one address against one account that cost nothing: a person mistypes.
PAIR_FREE_FAILURES = 5

#: Consecutive failures of one account, from every address, before unknown addresses wait (NIST SP 800-63B-4).
ACCOUNT_FREE_FAILURES = 100

#: Failures of one address, against any account, before it waits.
ADDRESS_FREE_FAILURES = 100

#: The longest wait, in seconds.
MAX_WAIT = 60.0

#: Attempts of one pair that may be under way beyond the free failures.
IN_FLIGHT_SLACK = 16

#: A key without failure for this long (seconds) starts again from zero.
FORGET_AFTER = 900.0
ACCOUNT_FORGET_AFTER = 3600.0

#: Addresses remembered per account as having signed in, and for how long.
KNOWN_ADDRESSES = 8
KNOWN_FOR = 30 * 86400.0

MAX_ENTRIES = 10_000


def address_key(ip: str) -> str:
    """The address a limit is kept for: an IPv6 address stands for its /64, since one host owns that many."""
    try:
        address = ipaddress.ip_address(ip)
    except ValueError:
        return ip
    if address.version == 6:
        if address.ipv4_mapped:
            return str(address.ipv4_mapped)
        return str(ipaddress.ip_network((int(address) >> 64 << 64, 64)))
    return str(address)


def _wait(failures: int, free: int) -> float:
    if failures < free:
        return 0.0
    return min(2.0 ** min(failures - free, 32), MAX_WAIT)


class _Counters:
    """Failure counts by key, least recently failed first. Idle entries make room; penalised ones never do."""

    def __init__(self, clock: Callable[[], float], free: int, forget_after: float, max_entries: int):
        self.clock = clock
        self.free = free
        self.forget_after = forget_after
        self.max_entries = max_entries
        self._entries: OrderedDict[str, tuple[int, float]] = OrderedDict()

    def __len__(self):
        return len(self._entries)

    def get(self, key: str) -> tuple[int, float]:
        """(failures, seconds since the last one); forgets what is old."""
        entry = self._entries.get(key)
        if entry is None:
            return 0, 0.0
        elapsed = self.clock() - entry[1]
        if elapsed >= self.forget_after:
            del self._entries[key]
            return 0, 0.0
        return entry[0], elapsed

    def wait(self, key: str) -> float:
        failures, elapsed = self.get(key)
        return max(0.0, _wait(failures, self.free) - elapsed)

    def add(self, key: str, weight: int = 1) -> bool:
        """Counts failures. False when there is no room: the entry is not recorded rather than a penalised one dropped."""
        failures, _ = self.get(key)
        if failures == 0 and not self._make_room():
            return False
        self._entries.pop(key, None)
        self._entries[key] = (failures + weight, self.clock())
        return True

    def clear(self, key: str) -> None:
        self._entries.pop(key, None)

    def _make_room(self) -> bool:
        if len(self._entries) < self.max_entries:
            return True
        now = self.clock()
        for key, (failures, last) in list(self._entries.items())[:128]:
            if failures < self.free or now - last >= self.forget_after:
                del self._entries[key]
                return True
        return False


@dataclass(frozen=True)
class Admitted:
    """The attempt may go on. Give it back to :meth:`SignInThrottle.end` with what became of it."""

    login: str
    address: str
    pair: str


@dataclass(frozen=True)
class Refused:
    """Over a limit: try again in ``retry_after`` seconds. Nothing was looked at."""

    retry_after: float


class SignInThrottle:
    def __init__(self, *, clock: Callable[[], float] = monotonic, max_entries: int = MAX_ENTRIES):
        self.clock = clock
        self.pairs = _Counters(clock, PAIR_FREE_FAILURES, FORGET_AFTER, max_entries)
        self.addresses = _Counters(clock, ADDRESS_FREE_FAILURES, FORGET_AFTER, max_entries)
        self.accounts = _Counters(clock, ACCOUNT_FREE_FAILURES, ACCOUNT_FORGET_AFTER, max_entries)
        # login -> address -> time of the last sign in
        self._known: OrderedDict[str, OrderedDict[str, float]] = OrderedDict()
        self._in_flight: dict[str, int] = {}
        self.max_entries = max_entries

    def __len__(self):
        return len(self.pairs) + len(self.addresses) + len(self.accounts)

    def _is_known(self, login: str, address: str) -> bool:
        seen = self._known.get(login, {}).get(address)
        return seen is not None and self.clock() - seen < KNOWN_FOR

    def retry_after(self, login: str, ip: str) -> float:
        """Seconds this address must still wait before it may try this account, 0 when it may."""
        address = address_key(ip)
        wait = max(self.pairs.wait(f"{login}\0{address}"), self.addresses.wait(address))
        if not self._is_known(login, address):
            wait = max(wait, self.accounts.wait(login))
        return wait

    def begin(self, login: str, ip: str) -> Admitted | Refused:
        """Starts an attempt, or refuses it."""
        if (wait := self.retry_after(login, ip)) > 0:
            return Refused(wait)
        address = address_key(ip)
        pair = f"{login}\0{address}"
        if self._in_flight.get(pair, 0) >= PAIR_FREE_FAILURES + IN_FLIGHT_SLACK:
            return Refused(1.0)
        self._in_flight[pair] = self._in_flight.get(pair, 0) + 1
        return Admitted(login, address, pair)

    def end(self, admitted: Admitted, outcome: str) -> None:
        """
        Closes an attempt: ``success`` (the password was right), ``failure`` (it is counted) or ``abandoned`` (it was
        never looked at, for lack of room: it is not).
        """
        left = self._in_flight.get(admitted.pair, 1) - 1
        if left > 0:
            self._in_flight[admitted.pair] = left
        else:
            self._in_flight.pop(admitted.pair, None)
        if outcome == "abandoned":
            return
        if outcome == "failure":
            recorded = self.pairs.add(admitted.pair)
            recorded = self.accounts.add(admitted.login) and recorded
            # a key with no room falls under its address, as if it had piled up penalised pairs
            self.addresses.add(admitted.address, 1 if recorded else 1 + PAIR_FREE_FAILURES)
            return
        # the pair and the account proved themselves; the address keeps its failures, or an attacker owning one valid
        # account would wash its guesses against the others
        self.pairs.clear(admitted.pair)
        self.accounts.clear(admitted.login)
        self._remember(admitted.login, admitted.address)

    def _remember(self, login: str, address: str) -> None:
        addresses = self._known.pop(login, OrderedDict())
        addresses.pop(address, None)
        addresses[address] = self.clock()
        while len(addresses) > KNOWN_ADDRESSES:
            addresses.popitem(last=False)
        self._known[login] = addresses
        while len(self._known) > self.max_entries:
            self._known.popitem(last=False)
