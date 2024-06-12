from harp_apps.dashboard.filters.base import NonExhaustiveFacet


def test_non_exhaustive_facet():
    facet = NonExhaustiveFacet()
    assert "NULL" in facet.choices
