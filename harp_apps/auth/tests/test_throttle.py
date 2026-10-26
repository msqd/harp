import pytest

from harp_apps.auth import throttle as module
from harp_apps.auth.throttle import (
    ACCOUNT_FREE_FAILURES,
    ADDRESS_FREE_FAILURES,
    IN_FLIGHT_SLACK,
    MAX_WAIT,
    PAIR_FREE_FAILURES,
    Admitted,
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

    assert 0 < throttle.retry_after("alice", "10.0.0.1") <= MAX_WAIT == 60.0


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


def test_an_abandoned_attempt_is_not_counted(throttle):
    for _ in range(PAIR_FREE_FAILURES + 5):
        throttle.end(throttle.begin("alice", "10.0.0.1"), "abandoned")

    assert throttle.retry_after("alice", "10.0.0.1") == 0


# --- parallel requests ---------------------------------------------------------------------------------------------


def test_parallel_valid_requests_are_never_refused_for_being_parallel(throttle):
    started = [throttle.begin("alice", "10.0.0.1") for _ in range(PAIR_FREE_FAILURES + IN_FLIGHT_SLACK)]
    assert all(isinstance(s, Admitted) for s in started)

    for admitted in started:
        throttle.end(admitted, "success")

    assert isinstance(throttle.begin("alice", "10.0.0.1"), Admitted)


def test_the_attempts_of_one_pair_under_way_at_once_are_bounded(throttle):
    started = [throttle.begin("alice", "10.0.0.1") for _ in range(200)]

    assert sum(isinstance(s, Admitted) for s in started) == PAIR_FREE_FAILURES + IN_FLIGHT_SLACK


def test_finished_attempts_make_room_for_others_of_the_pair(throttle):
    started = [throttle.begin("alice", "10.0.0.1") for _ in range(PAIR_FREE_FAILURES + IN_FLIGHT_SLACK)]
    throttle.end(started[0], "abandoned")

    assert isinstance(throttle.begin("alice", "10.0.0.1"), Admitted)


def test_a_burst_of_guesses_sent_at_once_stops_at_the_bound_then_meets_the_wait(throttle):
    started = [throttle.begin("alice", "10.0.0.1") for _ in range(200)]
    for admitted in started:
        if isinstance(admitted, Admitted):
            throttle.end(admitted, "failure")

    assert isinstance(throttle.begin("alice", "10.0.0.1"), Refused)


# --- the address ---------------------------------------------------------------------------------------------------


def test_an_address_that_piled_up_failures_is_refused_for_every_account(throttle):
    for i in range(ADDRESS_FREE_FAILURES):
        attempt(throttle, login=f"user{i // 5}")

    assert isinstance(throttle.begin("somebody", "10.0.0.1"), Refused)
    assert isinstance(throttle.begin("somebody", "10.0.0.2"), Admitted)


def test_the_wait_of_an_address_is_short(throttle):
    for i in range(ADDRESS_FREE_FAILURES * 3):
        attempt(throttle, login=f"user{i}")

    assert 0 < throttle.retry_after("somebody", "10.0.0.1") <= MAX_WAIT


def test_an_address_with_few_failures_is_not_refused(throttle):
    for i in range(ADDRESS_FREE_FAILURES - 1):
        attempt(throttle, login=f"user{i}")

    assert isinstance(throttle.begin("somebody", "10.0.0.1"), Admitted)


def test_a_success_does_not_wash_the_failures_of_the_address(throttle):
    for i in range(ADDRESS_FREE_FAILURES - 1):
        attempt(throttle, login=f"user{i}")
    attempt(throttle, login="alice", outcome="success")
    fail(throttle, 1, login="other")

    assert isinstance(throttle.begin("somebody", "10.0.0.1"), Refused)


@pytest.mark.parametrize(
    "ip, other",
    [("2001:db8:1:2::1", "2001:db8:1:2:ffff::9"), ("::ffff:192.0.2.7", "192.0.2.7")],
)
def test_addresses_of_one_host_share_their_key(ip, other):
    assert address_key(ip) == address_key(other)


def test_different_ipv6_networks_do_not_share_a_key():
    assert address_key("2001:db8:1:2::1") != address_key("2001:db8:1:3::1")


def test_an_ipv6_host_cannot_escape_the_wait_by_changing_address(throttle):
    for i in range(ADDRESS_FREE_FAILURES + 10):
        attempt(throttle, login=f"user{i}", ip=f"2001:db8:1:2::{i:x}")

    assert isinstance(throttle.begin("somebody", "2001:db8:1:2:aaaa::1"), Refused)


# --- the account ---------------------------------------------------------------------------------------------------


def hammer_account(throttle, times, login="victim"):
    for i in range(times):
        attempt(throttle, login=login, ip=f"198.51.{i // 250}.{i % 250}")


def test_an_account_does_not_wait_for_the_first_hundred_consecutive_failures(throttle):
    hammer_account(throttle, ACCOUNT_FREE_FAILURES - 1)

    assert isinstance(throttle.begin("victim", "203.0.113.9"), Admitted)


def test_then_unknown_addresses_are_refused_for_a_minute_at_most(throttle):
    hammer_account(throttle, ACCOUNT_FREE_FAILURES + 500)

    refused = throttle.begin("victim", "203.0.113.9")

    assert isinstance(refused, Refused) and 0 < refused.retry_after <= MAX_WAIT


def test_the_victim_gets_in_when_the_wait_is_over_whatever_the_attacker_does(throttle, clock):
    hammer_account(throttle, ACCOUNT_FREE_FAILURES + 500)
    clock.now += MAX_WAIT

    assert isinstance(throttle.begin("victim", "203.0.113.9"), Admitted)


def test_an_address_that_signed_in_before_is_not_refused_by_the_account(throttle):
    attempt(throttle, login="victim", ip="203.0.113.9", outcome="success")
    hammer_account(throttle, ACCOUNT_FREE_FAILURES + 500)

    assert isinstance(throttle.begin("victim", "203.0.113.9"), Admitted)


def test_a_success_clears_the_account(throttle, clock):
    hammer_account(throttle, ACCOUNT_FREE_FAILURES + 50)
    clock.now += MAX_WAIT

    attempt(throttle, login="victim", ip="203.0.113.5", outcome="success")

    assert len(throttle.accounts) == 0
    assert isinstance(throttle.begin("victim", "203.0.113.77"), Admitted)


def test_known_addresses_are_forgotten_after_a_long_time(throttle, clock):
    attempt(throttle, login="victim", ip="203.0.113.9", outcome="success")
    clock.now += module.KNOWN_FOR + 1
    hammer_account(throttle, ACCOUNT_FREE_FAILURES + 50)

    assert isinstance(throttle.begin("victim", "203.0.113.9"), Refused)


def test_only_a_few_addresses_are_remembered_per_account(throttle):
    for i in range(module.KNOWN_ADDRESSES + 2):
        attempt(throttle, login="victim", ip=f"203.0.113.{i}", outcome="success")
    hammer_account(throttle, ACCOUNT_FREE_FAILURES + 50)

    assert isinstance(throttle.begin("victim", "203.0.113.0"), Refused)
    assert isinstance(throttle.begin("victim", f"203.0.113.{module.KNOWN_ADDRESSES + 1}"), Admitted)


# --- the victim stays able to sign in -----------------------------------------------------------------------------


def test_a_victim_on_another_address_is_not_refused_by_the_guesses_at_their_name(throttle, clock):
    for step in range(PAIR_FREE_FAILURES * 3):
        clock.now += 1
        attempt(throttle, login="alice", ip="198.51.100.1")  # the attacker, from one address

    assert isinstance(throttle.begin("alice", "203.0.113.5"), Admitted)


def test_a_victim_whose_name_is_hammered_from_everywhere_waits_a_minute_at_most(throttle, clock):
    waits = []
    for step in range(3600):
        clock.now += 1
        attempt(throttle, login="alice", ip=f"198.51.{step // 250}.{step % 250}")
        waits.append(throttle.retry_after("alice", "203.0.113.5"))

    assert max(waits) <= MAX_WAIT
    clock.now += MAX_WAIT
    assert isinstance(throttle.begin("alice", "203.0.113.5"), Admitted)


# --- memory --------------------------------------------------------------------------------------------------------


def test_a_flood_of_fresh_names_and_addresses_does_not_wipe_a_penalty(clock):
    throttle = SignInThrottle(clock=clock, max_entries=200)
    fail(throttle, PAIR_FREE_FAILURES + 3, login="admin", ip="198.51.100.1")
    assert throttle.retry_after("admin", "198.51.100.1") > 0

    for i in range(5000):
        attempt(throttle, login=f"junk{i}", ip=f"2001:db8:{i:x}::1")

    assert throttle.retry_after("admin", "198.51.100.1") > 0


def test_penalised_entries_survive_while_idle_ones_make_room(clock):
    throttle = SignInThrottle(clock=clock, max_entries=50)
    for i in range(10):
        fail(throttle, PAIR_FREE_FAILURES, login=f"victim{i}", ip="198.51.100.1")

    for i in range(1000):
        attempt(throttle, login=f"junk{i}", ip=f"10.9.{i // 250}.{i % 250}")

    assert all(throttle.retry_after(f"victim{i}", "198.51.100.1") > 0 for i in range(10))
    assert len(throttle.pairs) <= 50


def test_a_table_full_of_penalised_pairs_does_not_free_the_address_that_filled_it(clock):
    """10 000 throwaway names, five failures each, from one address: the table is full of penalised pairs, and a
    guess at a name that has no room still meets the wait, as that of the address."""
    throttle = SignInThrottle(clock=clock, max_entries=100)
    for i in range(2000):
        for _ in range(PAIR_FREE_FAILURES):
            attempt(throttle, login=f"junk{i}", ip="203.0.113.7")
        clock.now += 0.06

    results = []
    for _ in range(200):
        results.append(throttle.begin("alice", "203.0.113.7"))
        if isinstance(results[-1], Admitted):
            throttle.end(results[-1], "failure")

    assert sum(isinstance(r, Refused) for r in results) >= 190


def test_a_guess_the_pair_table_has_no_room_for_falls_under_its_address(clock):
    throttle = SignInThrottle(clock=clock, max_entries=100)
    for i in range(100):  # the table of pairs, full of penalised entries, each from an address of its own
        fail(throttle, PAIR_FREE_FAILURES, login=f"victim{i}", ip=f"198.51.100.{i}")
    assert len(throttle.pairs) == 100

    results = []
    for _ in range(40):
        results.append(throttle.begin("alice", "203.0.113.7"))
        if isinstance(results[-1], Admitted):
            throttle.end(results[-1], "failure")

    assert any(isinstance(r, Refused) for r in results)  # 40 failures, but they weigh more than the free 100
    assert isinstance(throttle.begin("alice", "203.0.113.8"), Admitted)


def test_old_penalties_are_forgotten(throttle, clock):
    fail(throttle, PAIR_FREE_FAILURES + 2)

    clock.now += 3600

    assert throttle.retry_after("alice", "10.0.0.1") == 0


def test_a_success_from_an_address_with_no_failure_leaves_nothing_behind(throttle):
    attempt(throttle, outcome="success")

    assert len(throttle.pairs) == len(throttle.addresses) == len(throttle.accounts) == 0
