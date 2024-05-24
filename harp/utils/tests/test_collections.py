import pytest
from multidict import MultiDict

from harp.utils.collections import MultiChainMap


class TestMultiChainMap:
    def create_from_two_multidicts(self):
        child1 = MultiDict((("a", 1), ("b", 2), ("a", 3)))
        child2 = MultiDict((("b", 4), ("c", 5)))
        return MultiChainMap(child1, child2)

    def test_get_one_dict(self):
        c = MultiChainMap({"a": 1, "b": 2})
        assert c["a"] == 1
        assert c["b"] == 2
        with pytest.raises(KeyError):
            _ = c["c"]

    def test_get_two_dicts(self):
        c = MultiChainMap({"a": 1, "b": 2}, {"b": 3, "c": 4})
        assert c["a"] == 1
        assert c["b"] == 2
        assert c["c"] == 4
        with pytest.raises(KeyError):
            _ = c["d"]

    def test_empty(self):
        c = MultiChainMap()
        with pytest.raises(KeyError):
            _ = c["a"]

    def test_get_from_one_multi_dict(self):
        child = MultiDict((("a", 1), ("b", 2), ("a", 3)))
        wrapper = MultiChainMap(child)
        assert wrapper["a"] == 1
        assert wrapper["b"] == 2
        with pytest.raises(KeyError):
            _ = wrapper["c"]

    def test_get_from_two_multi_dict(self):
        c = self.create_from_two_multidicts()
        assert c["a"] == 1
        assert c["b"] == 2
        assert c["c"] == 5
        with pytest.raises(KeyError):
            _ = c["d"]

        assert dict(c) == {"a": 1, "b": 2, "c": 5}

    def test_items(self):
        c = self.create_from_two_multidicts()
        assert list(c.items()) == [("b", 2), ("c", 5), ("a", 1), ("a", 3)]

    def test_iter(self):
        c = self.create_from_two_multidicts()

        ci = iter(c)
        assert next(ci) == "b"
        assert next(ci) == "c"
        assert next(ci) == "a"
        assert next(ci) == "a"
        with pytest.raises(StopIteration):
            next(ci)

    def test_len(self):
        assert len(self.create_from_two_multidicts()) == 4

    def test_contains(self):
        c = self.create_from_two_multidicts()
        assert "a" in c
        assert "b" in c
        assert "c" in c
        assert "d" not in c

    def test_notset(self):
        c = self.create_from_two_multidicts()

        assert "b" in c
        del c["b"]
        assert "b" not in c

        # "b" source was not touched
        assert "b" in c.maps[1]
