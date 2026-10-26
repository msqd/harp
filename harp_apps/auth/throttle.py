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
(:data:`PAIR_FREE_FAILURES` + :data:`IN_FLIGHT_SLACK`), and the hashing queue bounds the rest. A key over its free
failures lets one attempt through at a time, so a burst arriving as a wait runs out gets one guess. Idle keys make room in
a full table, oldest first, and an address the table cannot record is refused rather than let in unseen.

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

#: Attempts of one address that may be under way at once, whoever they are for.
MAX_IN_FLIGHT_PER_ADDRESS = 32

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
    """
    Failure counts by key, least recently failed first. Keys under their free failures are *idle*: they make room, oldest
    first, however many penalised keys come before them. A penalised key is dropped only when it is old enough to be
    forgotten.
    """

    def __init__(self, clock: Callable[[], float], free: int, forget_after: float, max_entries: int):
        self.clock = clock
        self.free = free
        self.forget_after = forget_after
        self.max_entries = max_entries
        self._entries: OrderedDict[str, tuple[int, float]] = OrderedDict()
        self._idle: OrderedDict[str, None] = OrderedDict()

    def __len__(self):
        return len(self._entries)

    def _drop(self, key: str) -> None:
        self._entries.pop(key, None)
        self._idle.pop(key, None)

    def get(self, key: str) -> tuple[int, float]:
        """(failures, seconds since the last one); forgets what is old."""
        entry = self._entries.get(key)
        if entry is None:
            return 0, 0.0
        elapsed = self.clock() - entry[1]
        if elapsed >= self.forget_after:
            self._drop(key)
            return 0, 0.0
        return entry[0], elapsed

    def failures(self, key: str) -> int:
        return self.get(key)[0]

    def wait(self, key: str) -> float:
        failures, elapsed = self.get(key)
        return max(0.0, _wait(failures, self.free) - elapsed)

    def has_room_for(self, key: str) -> bool:
        """Whether a failure of this key can be recorded."""
        return self.get(key)[0] > 0 or self._make_room(dry_run=True)

    def add(self, key: str, weight: int = 1) -> bool:
        """Counts failures. False when there is no room: the entry is not recorded rather than a penalised one dropped."""
        failures, _ = self.get(key)
        if failures == 0 and not self._make_room():
            return False
        self._drop(key)
        failures += weight
        self._entries[key] = (failures, self.clock())
        if failures < self.free:
            self._idle[key] = None
        return True

    def clear(self, key: str) -> None:
        self._drop(key)

    def _make_room(self, dry_run: bool = False) -> bool:
        if len(self._entries) < self.max_entries:
            return True
        if self._idle:
            if not dry_run:
                self._drop(next(iter(self._idle)))
            return True
        oldest = next(iter(self._entries), None)
        if oldest is not None and self.clock() - self._entries[oldest][1] >= self.forget_after:
            if not dry_run:
                self._drop(oldest)
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
        self._in_flight_accounts: dict[str, int] = {}
        self._in_flight_addresses: dict[str, int] = {}
        self.max_entries = max_entries

    def __len__(self):
        return len(self.pairs) + len(self.addresses) + len(self.accounts)

    def _is_known(self, login: str, address: str) -> bool:
        seen = self._known.get(login, {}).get(address)
        return seen is not None and self.clock() - seen < KNOWN_FOR

    def retry_after(self, login: str, ip: str) -> float:
        """Seconds this address must still wait before it may try this account, 0 when it may."""
        address = address_key(ip)
        wait = self.pairs.wait(f"{login}\0{address}")
        if not self._is_known(login, address):
            # an address an account signed in from reaches that account whatever floods the address or the account
            wait = max(wait, self.addresses.wait(address), self.accounts.wait(login))
        return wait

    def begin(self, login: str, ip: str) -> Admitted | Refused:
        """
        Starts an attempt, or refuses it. A key over its free failures lets one attempt through at a time: the wait is
        checked here and the failure counted at :meth:`end`, so without that every attempt arriving together when a wait
        runs out would pass.
        """
        if (wait := self.retry_after(login, ip)) > 0:
            return Refused(wait)
        address = address_key(ip)
        pair = f"{login}\0{address}"
        known = self._is_known(login, address)
        if not known and not self.addresses.has_room_for(address):
            return Refused(MAX_WAIT)  # nothing could be recorded about this address: it is not let in unseen
        if self._in_flight_addresses.get(address, 0) >= (
            1 if self.addresses.failures(address) >= ADDRESS_FREE_FAILURES else MAX_IN_FLIGHT_PER_ADDRESS
        ):
            return Refused(1.0)
        pair_limit = 1 if self.pairs.failures(pair) >= PAIR_FREE_FAILURES else PAIR_FREE_FAILURES + IN_FLIGHT_SLACK
        if self._in_flight.get(pair, 0) >= pair_limit:
            return Refused(1.0)
        if not known and self.accounts.failures(login) >= ACCOUNT_FREE_FAILURES:
            if self._in_flight_accounts.get(login, 0) >= 1:
                return Refused(1.0)
        self._in_flight[pair] = self._in_flight.get(pair, 0) + 1
        self._in_flight_addresses[address] = self._in_flight_addresses.get(address, 0) + 1
        self._in_flight_accounts[login] = self._in_flight_accounts.get(login, 0) + 1
        return Admitted(login, address, pair)

    def end(self, admitted: Admitted, outcome: str) -> None:
        """
        Closes an attempt: ``success`` (the password was right), ``failure`` (it is counted) or ``abandoned`` (it was
        never looked at, for lack of room: it is not).
        """
        for counts, key in (
            (self._in_flight, admitted.pair),
            (self._in_flight_accounts, admitted.login),
            (self._in_flight_addresses, admitted.address),
        ):
            if (left := counts.get(key, 1) - 1) > 0:
                counts[key] = left
            else:
                counts.pop(key, None)
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
