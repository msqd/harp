import pytest

from harp_apps.auth import throttle as module
from harp_apps.auth.throttle import (
    ACCOUNT_FREE_FAILURES,
    ADDRESS_FREE_FAILURES,
    MAX_DELAY,
    MAX_IN_FLIGHT,
    PAIR_FREE_FAILURES,
    Admitted,
    Busy,
    Refused,
    SignInThrottle,
    address_key,
)


class Clock:
    now = 1000.0

    def __call__(self):
        return self.now


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def throttle(clock):
    return SignInThrottle(clock=clock)


def attempt(throttle, login="alice", ip="10.0.0.1", outcome="failure"):
    admitted = throttle.begin(login, ip)
    if isinstance(admitted, Admitted):
        throttle.end(admitted, outcome)
    return admitted


def fail(throttle, times, login="alice", ip="10.0.0.1"):
    for _ in range(times):
        attempt(throttle, login, ip)


# --- the pair: one address against one account ---------------------------------------------------------------------


def test_the_first_failures_cost_nothing(throttle):
    fail(throttle, PAIR_FREE_FAILURES - 1)

    assert isinstance(throttle.begin("alice", "10.0.0.1"), Admitted)


def test_the_pair_is_then_refused_for_longer_each_time(throttle, clock):
    waits = []
    for _ in range(PAIR_FREE_FAILURES + 3):
        fail(throttle, 1)
        waits.append(throttle.retry_after("alice", "10.0.0.1"))
        clock.now += waits[-1]

    positive = [w for w in waits if w > 0]
    assert positive == sorted(positive) and len(set(positive)) == len(positive) >= 3


def test_a_refused_attempt_is_not_counted_and_does_not_extend_the_wait(throttle):
    fail(throttle, PAIR_FREE_FAILURES)
    before = throttle.retry_after("alice", "10.0.0.1")

    results = [throttle.begin("alice", "10.0.0.1") for _ in range(20)]

    assert all(isinstance(r, Refused) for r in results)
    assert throttle.retry_after("alice", "10.0.0.1") <= before


def test_the_wait_runs_out_with_time(throttle, clock):
    fail(throttle, PAIR_FREE_FAILURES)
    clock.now += throttle.retry_after("alice", "10.0.0.1")

    assert isinstance(throttle.begin("alice", "10.0.0.1"), Admitted)


def test_the_wait_is_short_and_never_a_lockout(throttle):
    fail(throttle, 1000)

    assert 0 < throttle.retry_after("alice", "10.0.0.1") <= MAX_DELAY == 60.0


def test_another_address_against_the_same_account_is_not_refused(throttle):
    fail(throttle, PAIR_FREE_FAILURES * 3, ip="10.0.0.1")

    assert isinstance(throttle.begin("alice", "10.0.0.2"), Admitted)


def test_the_same_address_against_another_account_is_not_refused(throttle):
    fail(throttle, PAIR_FREE_FAILURES * 3, login="alice")

    assert isinstance(throttle.begin("bob", "10.0.0.1"), Admitted)


def test_a_success_clears_the_pair(throttle):
    fail(throttle, PAIR_FREE_FAILURES - 1)

    attempt(throttle, outcome="success")
    fail(throttle, PAIR_FREE_FAILURES - 1)

    assert isinstance(throttle.begin("alice", "10.0.0.1"), Admitted)


def test_guesses_sent_at_once_meet_the_wait_as_the_others_do(throttle):
    admitted = [throttle.begin("alice", "10.0.0.1") for _ in range(40)]

    assert sum(isinstance(a, Admitted) for a in admitted) == PAIR_FREE_FAILURES


# --- the address ---------------------------------------------------------------------------------------------------


def test_an_address_is_delayed_after_many_failures_and_never_refused(throttle):
    for i in range(ADDRESS_FREE_FAILURES + 50):
        attempt(throttle, login=f"user{i}")

    admitted = throttle.begin("somebody", "10.0.0.1")

    assert isinstance(admitted, Admitted) and 0 < admitted.delay <= module.ADDRESS_MAX_DELAY


def test_the_delay_of_an_address_is_short(throttle):
    for i in range(ADDRESS_FREE_FAILURES * 20):
        attempt(throttle, login=f"user{i}")

    assert throttle.begin("somebody", "10.0.0.1").delay == module.ADDRESS_MAX_DELAY <= 10


def test_an_address_with_few_failures_is_not_delayed(throttle):
    for i in range(ADDRESS_FREE_FAILURES - 1):
        attempt(throttle, login=f"user{i}")

    assert throttle.begin("somebody", "10.0.0.1").delay == 0


def test_a_success_gives_back_its_own_attempt_to_the_address_and_nothing_more(throttle):
    for i in range(ADDRESS_FREE_FAILURES - 2):
        attempt(throttle, login=f"user{i}")
    attempt(throttle, login="alice", outcome="success")  # reserved, then given back

    assert throttle.delay_for("somebody", "10.0.0.1") == 0
    attempt(throttle, login="other")  # one more failure
    assert throttle.delay_for("somebody", "10.0.0.1") == 0  # exactly the free ones
    attempt(throttle, login="other2")
    assert throttle.delay_for("somebody", "10.0.0.1") > 0


@pytest.mark.parametrize(
    "ip, other",
    [("2001:db8:1:2::1", "2001:db8:1:2:ffff::9"), ("::ffff:192.0.2.7", "192.0.2.7")],
)
def test_addresses_of_one_host_share_their_key(ip, other):
    assert address_key(ip) == address_key(other)


def test_different_ipv6_networks_do_not_share_a_key():
    assert address_key("2001:db8:1:2::1") != address_key("2001:db8:1:3::1")


def test_an_ipv6_host_cannot_escape_the_delay_by_changing_address(throttle):
    for i in range(ADDRESS_FREE_FAILURES + 10):
        attempt(throttle, login=f"user{i}", ip=f"2001:db8:1:2::{i:x}")

    assert throttle.begin("somebody", "2001:db8:1:2:aaaa::1").delay > 0


# --- the account ---------------------------------------------------------------------------------------------------


def hammer_account(throttle, times, login="victim"):
    for i in range(times):
        attempt(throttle, login=login, ip=f"198.51.{i // 250}.{i % 250}")


def test_an_account_is_not_delayed_for_the_first_hundred_consecutive_failures(throttle):
    hammer_account(throttle, ACCOUNT_FREE_FAILURES - 1)

    assert throttle.begin("victim", "203.0.113.9").delay == 0


def test_then_unknown_addresses_are_delayed_a_little_and_never_refused(throttle):
    hammer_account(throttle, ACCOUNT_FREE_FAILURES + 30)

    admitted = throttle.begin("victim", "203.0.113.9")

    assert isinstance(admitted, Admitted) and 0 < admitted.delay <= MAX_DELAY


def test_the_account_delay_is_capped_short(throttle):
    hammer_account(throttle, ACCOUNT_FREE_FAILURES + 500)

    assert throttle.begin("victim", "203.0.113.9").delay == MAX_DELAY


def test_an_address_that_signed_in_before_is_not_delayed_by_the_account(throttle):
    attempt(throttle, login="victim", ip="203.0.113.9", outcome="success")
    hammer_account(throttle, ACCOUNT_FREE_FAILURES + 500)

    assert throttle.begin("victim", "203.0.113.9").delay == 0


def test_a_success_clears_the_account(throttle):
    hammer_account(throttle, ACCOUNT_FREE_FAILURES + 50)

    attempt(throttle, login="victim", ip="203.0.113.9", outcome="success")

    assert throttle.begin("victim", "203.0.113.10").delay == 0


def test_known_addresses_are_forgotten_after_a_long_time(throttle, clock):
    attempt(throttle, login="victim", ip="203.0.113.9", outcome="success")
    hammer_account(throttle, ACCOUNT_FREE_FAILURES + 50)
    clock.now += module.KNOWN_FOR + 1
    hammer_account(throttle, ACCOUNT_FREE_FAILURES + 50)

    assert throttle.begin("victim", "203.0.113.9").delay > 0


def test_only_a_few_addresses_are_remembered_per_account(throttle):
    for i in range(module.KNOWN_ADDRESSES + 2):
        attempt(throttle, login="victim", ip=f"203.0.113.{i}", outcome="success")
    hammer_account(throttle, ACCOUNT_FREE_FAILURES + 50)

    assert throttle.begin("victim", "203.0.113.0").delay > 0
    assert throttle.begin("victim", f"203.0.113.{module.KNOWN_ADDRESSES + 1}").delay == 0


# --- the victim stays able to sign in -----------------------------------------------------------------------------


def test_a_victim_behind_a_shared_address_is_never_refused(throttle, clock):
    """Everybody comes from the address of the reverse proxy; one attacker guesses there all day."""
    refused = 0
    for step in range(0, 86400, 10):
        clock.now = 1000.0 + step
        attempt(throttle, login=f"guess{step}", ip="10.0.0.1")
        result = throttle.begin("alice", "10.0.0.1")
        if isinstance(result, Refused):
            refused += 1
        else:
            throttle.end(result, "success")

    assert refused == 0


def test_a_victim_whose_name_is_hammered_waits_a_bounded_time_and_is_never_refused(throttle, clock):
    worst = 0.0
    for step in range(0, 3600):
        clock.now = 1000.0 + step
        attempt(
            throttle, login="alice", ip=f"198.51.{step // 250}.{step % 250}"
        )  # the attacker, a new address each time
        result = throttle.begin("alice", "203.0.113.5")  # the victim, from their own address
        assert isinstance(result, Admitted)
        worst = max(worst, result.delay)
        throttle.end(result, "abandoned")  # looked at, not counted: only the delay is what is measured here

    assert worst == MAX_DELAY


# --- memory --------------------------------------------------------------------------------------------------------


def test_a_flood_of_fresh_names_and_addresses_does_not_wipe_a_penalty(clock):
    throttle = SignInThrottle(clock=clock, max_entries=200)
    fail(throttle, PAIR_FREE_FAILURES + 3, login="admin", ip="198.51.100.1")
    wait = throttle.retry_after("admin", "198.51.100.1")
    assert wait > 0

    for i in range(5000):
        attempt(throttle, login=f"junk{i}", ip=f"2001:db8:{i:x}::1")

    assert throttle.retry_after("admin", "198.51.100.1") > 0


def test_penalised_entries_survive_while_idle_ones_make_room(clock):
    throttle = SignInThrottle(clock=clock, max_entries=50)
    for i in range(10):
        fail(throttle, PAIR_FREE_FAILURES, login=f"victim{i}", ip="198.51.100.1")

    for i in range(1000):
        attempt(throttle, login=f"junk{i}", ip="10.9.9.9")

    assert all(throttle.retry_after(f"victim{i}", "198.51.100.1") > 0 for i in range(10))
    assert len(throttle.pairs) <= 50


def test_old_penalties_are_forgotten(throttle, clock):
    fail(throttle, PAIR_FREE_FAILURES + 2)

    clock.now += 3600

    assert throttle.retry_after("alice", "10.0.0.1") == 0


# --- room ----------------------------------------------------------------------------------------------------------


def test_too_many_attempts_under_way_are_answered_at_once_and_not_counted(throttle):
    held = [throttle.begin(f"user{i}", f"10.1.{i // 250}.{i % 250}") for i in range(MAX_IN_FLIGHT)]
    assert all(isinstance(h, Admitted) for h in held)

    assert isinstance(throttle.begin("alice", "10.0.0.1"), Busy)
    assert throttle.retry_after("alice", "10.0.0.1") == 0


def test_finished_attempts_make_room(throttle):
    held = [throttle.begin(f"user{i}", f"10.1.{i // 250}.{i % 250}") for i in range(MAX_IN_FLIGHT)]
    throttle.end(held[0], "failure")

    assert isinstance(throttle.begin("alice", "10.0.0.1"), Admitted)


def test_an_abandoned_attempt_is_not_counted(throttle):
    for _ in range(PAIR_FREE_FAILURES + 5):
        admitted = throttle.begin("alice", "10.0.0.1")
        throttle.end(admitted, "abandoned")

    assert throttle.retry_after("alice", "10.0.0.1") == 0
