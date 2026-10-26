from datetime import timedelta

import pytest

from harp.sweeps import Sweep, SweepBudget, SweepRegistry


async def nothing(budget: SweepBudget) -> int:
    return 0


def make_sweep(name="things.purge", **kwargs) -> Sweep:
    return Sweep(name=name, interval=None, budget=SweepBudget(), run=nothing, **kwargs)


class TestSweepBudget:
    def test_is_unlimited_by_default(self):
        budget = SweepBudget()

        assert budget.seconds is None
        assert budget.items is None

    @pytest.mark.parametrize("kwargs", [{"seconds": 0}, {"seconds": -1}, {"items": 0}, {"items": -5}])
    def test_rejects_a_limit_that_allows_nothing(self, kwargs):
        with pytest.raises(ValueError):
            SweepBudget(**kwargs)


class TestSweep:
    def test_rejects_an_interval_that_is_not_positive(self):
        with pytest.raises(ValueError):
            Sweep(name="x", interval=timedelta(0), budget=SweepBudget(), run=nothing)

    def test_rejects_an_empty_name(self):
        with pytest.raises(ValueError):
            Sweep(name="", interval=None, budget=SweepBudget(), run=nothing)


class TestSweepRegistry:
    def test_lists_declared_sweeps_in_declaration_order(self):
        registry = SweepRegistry()
        first, second = make_sweep("a.first"), make_sweep("b.second")

        registry.declare(first)
        registry.declare(second)

        assert list(registry) == [first, second]
        assert len(registry) == 2

    def test_refuses_two_sweeps_with_one_name(self):
        registry = SweepRegistry()
        registry.declare(make_sweep("a.same"))

        with pytest.raises(ValueError, match="a.same"):
            registry.declare(make_sweep("a.same"))

    def test_nothing_is_scheduled_until_a_scheduler_says_so(self):
        registry = SweepRegistry()
        registry.declare(make_sweep("a.one"))
        registry.declare(make_sweep("b.two"))

        assert registry.unscheduled == ["a.one", "b.two"]

        registry.mark_scheduled()

        assert registry.unscheduled == []

    def test_an_empty_registry_has_nothing_unscheduled(self):
        assert SweepRegistry().unscheduled == []
