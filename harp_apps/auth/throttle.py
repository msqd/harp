"""Slowing down who guesses passwords, without letting anyone slow down somebody else.

An attacker who only knows a name, or who shares an address with everybody (a reverse proxy), must not be able to keep a
person out. So the limits are not one counter but three, each with a different consequence:

* **per account and address** (the pair): from the fifth failure of one address against one account, that address has
  to wait before its next attempt (1 s, 2 s, 4 s ... :data:`MAX_DELAY`), and an attempt made too early is *refused*
  without looking at the password. Somebody guessing at ``alice`` from their address only slows themselves down: another
  address is another pair.
* **per address** (IPv6 by /64): after :data:`ADDRESS_FREE_FAILURES` failures, attempts are *delayed* (never refused) by
  a little more each time, up to :data:`ADDRESS_MAX_DELAY`. A shared address full of people mistyping, or of one
  attacker, makes everybody there wait a few seconds, nothing more.
* **per account** (every address together): NIST SP 800-63B-4 allows 100 consecutive failures; after that the attempts
  of addresses that never signed in to the account are *delayed* 1 s, 2 s ... :data:`MAX_DELAY`, and a person signing
  in from an address that did before is not delayed at all. Whoever hammers a name delays an unknown address by at most
  :data:`MAX_DELAY` seconds and never refuses it.

Attempts are counted as failures when they start and given back on success, so guesses sent at once meet the limits as
the later ones do. Entries still under penalty are never evicted to make room: a flood of fresh names and addresses
leaves the waits where they are (it only stops *new* entries from being recorded when the table is full of penalised
ones). Counts are per process and in memory: with several workers an attacker gets as many guesses as there are workers.
"""

import ipaddress
from collections import OrderedDict
from dataclasses import dataclass
from time import monotonic
from typing import Callable

#: Failures of one address against one account that cost nothing: a person mistypes.
PAIR_FREE_FAILURES = 5

#: Consecutive failures of one account, from every address, before unknown addresses are delayed (NIST SP 800-63B-4).
ACCOUNT_FREE_FAILURES = 100

#: Failures of one address, against any account, before it is delayed.
ADDRESS_FREE_FAILURES = 100

#: The longest wait or delay of a pair or an account, in seconds.
MAX_DELAY = 60.0

#: The longest delay of an address, in seconds, and how much each failure over the free ones adds.
ADDRESS_MAX_DELAY = 10.0
ADDRESS_DELAY_STEP = 0.1

#: A key without failure for this long (seconds) starts again from zero.
FORGET_AFTER = 900.0
ACCOUNT_FORGET_AFTER = 3600.0

#: Addresses remembered per account as having signed in, and for how long.
KNOWN_ADDRESSES = 8
KNOWN_FOR = 30 * 86400.0

MAX_ENTRIES = 10_000

#: Attempts under way (waiting out a delay or being checked), all together. More are answered at once.
MAX_IN_FLIGHT = 2000


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


def _doubling(failures: int, free: int) -> float:
    if failures < free:
        return 0.0
    return min(2.0 ** min(failures - free, 32), MAX_DELAY)


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

    def add(self, key: str) -> None:
        failures, _ = self.get(key)
        if failures == 0 and not self._make_room():
            return  # full of penalised entries: this one is not recorded rather than one of them forgotten
        self._entries.pop(key, None)
        self._entries[key] = (failures + 1, self.clock())

    def take_back(self, key: str) -> None:
        entry = self._entries.get(key)
        if entry is None:
            return
        if entry[0] <= 1:
            del self._entries[key]
        else:
            self._entries[key] = (entry[0] - 1, entry[1])

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
    """The attempt may go on, after ``delay`` seconds. Give it back to :meth:`SignInThrottle.end`."""

    delay: float
    login: str
    address: str
    pair: str


@dataclass(frozen=True)
class Refused:
    """Too early for this address against this account: try again in ``retry_after`` seconds. Nothing was looked at."""

    retry_after: float


@dataclass(frozen=True)
class Busy:
    """Too many attempts are waiting: nothing is recorded, try again in a moment."""

    retry_after: float = 1.0


class SignInThrottle:
    def __init__(self, *, clock: Callable[[], float] = monotonic, max_entries: int = MAX_ENTRIES):
        self.clock = clock
        self.pairs = _Counters(clock, PAIR_FREE_FAILURES, FORGET_AFTER, max_entries)
        self.addresses = _Counters(clock, ADDRESS_FREE_FAILURES, FORGET_AFTER, max_entries)
        self.accounts = _Counters(clock, ACCOUNT_FREE_FAILURES, ACCOUNT_FORGET_AFTER, max_entries)
        # login -> address -> time of the last sign in
        self._known: OrderedDict[str, OrderedDict[str, float]] = OrderedDict()
        self.max_entries = max_entries
        self._in_flight = 0

    def __len__(self):
        return len(self.pairs) + len(self.addresses) + len(self.accounts)

    def _is_known(self, login: str, address: str) -> bool:
        seen = self._known.get(login, {}).get(address)
        return seen is not None and self.clock() - seen < KNOWN_FOR

    def retry_after(self, login: str, ip: str) -> float:
        """Seconds the pair must still wait before it may try, 0 when it may."""
        failures, elapsed = self.pairs.get(f"{login}\0{address_key(ip)}")
        return max(0.0, _doubling(failures, PAIR_FREE_FAILURES) - elapsed)

    def delay_for(self, login: str, ip: str) -> float:
        """Seconds an attempt is held before its password is looked at."""
        address = address_key(ip)
        failures, _ = self.addresses.get(address)
        delay = min(ADDRESS_MAX_DELAY, max(0, failures - ADDRESS_FREE_FAILURES + 1) * ADDRESS_DELAY_STEP)
        if not self._is_known(login, address):
            failures, _ = self.accounts.get(login)
            delay = max(delay, _doubling(failures + 1, ACCOUNT_FREE_FAILURES + 1))
        return delay

    def begin(self, login: str, ip: str) -> Admitted | Refused | Busy:
        """
        Starts an attempt: refused when the pair is waiting, else counted as a failure from now (taken back by
        :meth:`end` on success) and told how long to be held.
        """
        if (wait := self.retry_after(login, ip)) > 0:
            return Refused(wait)
        if self._in_flight >= MAX_IN_FLIGHT:
            return Busy()
        address = address_key(ip)
        pair = f"{login}\0{address}"
        delay = self.delay_for(login, ip)
        self.pairs.add(pair)
        self.addresses.add(address)
        self.accounts.add(login)
        self._in_flight += 1
        return Admitted(delay, login, address, pair)

    def end(self, admitted: Admitted, outcome: str) -> None:
        """
        Closes an attempt: ``success`` (the password was right), ``failure`` (it stays counted) or ``abandoned`` (it was
        never looked at, for lack of room: it is not counted).
        """
        self._in_flight = max(0, self._in_flight - 1)
        if outcome == "failure":
            return
        if outcome == "abandoned":
            self.pairs.take_back(admitted.pair)
            self.addresses.take_back(admitted.address)
            self.accounts.take_back(admitted.login)
            return
        # the pair and the account proved themselves; the address gets this attempt back and keeps its other failures,
        # or an attacker owning one valid account would wash its guesses against the others
        self.pairs.clear(admitted.pair)
        self.accounts.clear(admitted.login)
        self.addresses.take_back(admitted.address)
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
