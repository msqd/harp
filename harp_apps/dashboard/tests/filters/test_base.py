from multidict import MultiDict

from harp_apps.dashboard.filters.base import AbstractMinMaxFacet, NonExhaustiveFacet


def test_non_exhaustive_facet():
    facet = NonExhaustiveFacet()
    assert "NULL" in facet.choices


class TestAbstractMinMaxFacet:
    facet = AbstractMinMaxFacet()

    def test_values(self):
        self.facet.meta = {"min": 10, "max": 90}
        assert self.facet.values == {"min": 10, "max": 90}

    def test_filter(self):
        result = self.facet.filter(10, 90)
        assert result == {"values": ["min", "max"], "current": {"min": 10, "max": 90}}

    def test_filter_from_query(self):
        self.facet.name = "test"
        query = MultiDict({"testmin": "10", "testmax": "90"})
        result = self.facet.filter_from_query(query)
        assert result == {
            "values": ["min", "max"],
            "current": {"min": 10.0, "max": 90.0},
        }

    def test_get_filter(self):
        result = self.facet.get_filter(10, 90)
        assert result == {"min": 10, "max": 90}

    def test_get_filter_from_query(self):
        self.facet.name = "test"
        query = MultiDict({"testmin": "10", "testmax": "90"})
        result = self.facet.get_filter_from_query(query)
        assert result == {"min": 10.0, "max": 90.0}

    def test_min_max_from_query(self):
        self.facet.name = "test"
        query = MultiDict({"testmin": "10", "testmax": "90"})
        result = self.facet._min_max_from_query(query)
        assert result == (10.0, 90.0)
