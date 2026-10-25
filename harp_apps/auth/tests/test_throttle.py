import pytest

from harp_apps.auth.throttle import FREE_FAILURES, MAX_DELAY, SignInThrottle


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


def fail(throttle, times, username="alice", ip="10.0.0.1"):
    for _ in range(times):
        throttle.failed(username, ip)


def test_the_first_failures_cost_nothing(throttle):
    fail(throttle, FREE_FAILURES - 1)

    assert throttle.retry_after("alice", "10.0.0.1") == 0


def test_further_failures_make_the_next_attempt_wait_longer_each_time(throttle, clock):
    delays = []
    for _ in range(FREE_FAILURES + 3):
        fail(throttle, 1)
        delays.append(throttle.retry_after("alice", "10.0.0.1"))
        clock.now += delays[-1]

    waits = [d for d in delays if d > 0]
    assert waits == sorted(waits) and len(set(waits)) == len(waits) >= 3


def test_the_wait_runs_out_with_time(throttle, clock):
    fail(throttle, FREE_FAILURES)
    wait = throttle.retry_after("alice", "10.0.0.1")
    assert wait > 0

    clock.now += wait

    assert throttle.retry_after("alice", "10.0.0.1") == 0


def test_the_wait_is_never_a_lockout(throttle):
    fail(throttle, 1000)

    assert 0 < throttle.retry_after("alice", "10.0.0.1") <= MAX_DELAY


def test_an_account_under_attack_waits_whatever_the_address(throttle):
    fail(throttle, FREE_FAILURES, username="alice", ip="10.0.0.1")

    assert throttle.retry_after("alice", "10.0.0.2") > 0


def test_an_address_under_attack_waits_whatever_the_account(throttle):
    fail(throttle, FREE_FAILURES, username="alice", ip="10.0.0.1")

    assert throttle.retry_after("bob", "10.0.0.1") > 0


def test_other_accounts_and_addresses_are_not_slowed(throttle):
    fail(throttle, FREE_FAILURES * 3, username="alice", ip="10.0.0.1")

    assert throttle.retry_after("bob", "10.0.0.2") == 0


def test_a_success_clears_the_account_and_not_the_address(throttle):
    fail(throttle, FREE_FAILURES, username="alice", ip="10.0.0.1")

    throttle.succeeded("alice", "10.0.0.2")

    assert throttle.retry_after("alice", "10.0.0.2") == 0
    assert throttle.retry_after("bob", "10.0.0.1") > 0  # the address cannot clean itself with a valid account


def test_a_success_takes_back_only_its_own_attempt_from_the_address(throttle):
    fail(throttle, FREE_FAILURES - 2, username="alice", ip="10.0.0.1")

    throttle.failed("alice", "10.0.0.1")  # the attempt, counted before it is answered
    throttle.succeeded("alice", "10.0.0.1")  # and it was right
    fail(throttle, 1, username="bob", ip="10.0.0.1")  # one failure short of the wait...
    assert throttle.retry_after("carol", "10.0.0.1") == 0
    fail(throttle, 1, username="bob", ip="10.0.0.1")  # ...the same as if the success had never happened

    assert throttle.retry_after("carol", "10.0.0.1") > 0


def test_a_success_from_an_address_with_no_failure_leaves_nothing_behind(throttle):
    throttle.failed("alice", "10.0.0.1")
    throttle.succeeded("alice", "10.0.0.1")

    assert len(throttle) == 0


def test_old_failures_are_forgotten(throttle, clock):
    fail(throttle, FREE_FAILURES + 2)

    clock.now += 3600

    fail(throttle, 1)
    assert throttle.retry_after("alice", "10.0.0.1") == 0


def test_the_memory_is_bounded(clock):
    throttle = SignInThrottle(clock=clock, max_entries=10)

    for i in range(100):
        throttle.failed(f"user{i}", f"10.0.0.{i}")

    assert len(throttle) <= 10
