import sys


def _harp_modules():
    """Currently imported ``harp`` and ``harp.*`` modules."""
    return {name: mod for name, mod in sys.modules.items() if name == "harp" or name.startswith("harp.")}


class TestDebugFlag:
    """Tests for the harp.DEBUG constant."""

    def _reload_harp_debug(self):
        """Reload harp module to re-evaluate DEBUG constant, then put back the original modules.

        Leaving the fresh modules in place would give later imports class objects distinct from the
        ones test modules imported earlier, breaking isinstance checks across the whole session.
        """
        saved = _harp_modules()
        for name in saved:
            del sys.modules[name]
        try:
            import harp

            return harp.DEBUG
        finally:
            for name in _harp_modules():
                del sys.modules[name]
            sys.modules.update(saved)

    def test_debug_is_false_when_no_env_vars_set(self, monkeypatch):
        monkeypatch.delenv("DEBUG", raising=False)
        monkeypatch.delenv("HARP_DEBUG", raising=False)
        assert self._reload_harp_debug() is False

    def test_debug_is_true_when_debug_env_var_set(self, monkeypatch):
        monkeypatch.delenv("HARP_DEBUG", raising=False)
        monkeypatch.setenv("DEBUG", "1")
        assert self._reload_harp_debug() is True

    def test_debug_is_true_when_harp_debug_env_var_set(self, monkeypatch):
        monkeypatch.delenv("DEBUG", raising=False)
        monkeypatch.setenv("HARP_DEBUG", "1")
        assert self._reload_harp_debug() is True

    def test_debug_is_true_when_both_env_vars_set(self, monkeypatch):
        monkeypatch.setenv("DEBUG", "1")
        monkeypatch.setenv("HARP_DEBUG", "1")
        assert self._reload_harp_debug() is True

    def test_debug_is_false_when_env_vars_are_empty(self, monkeypatch):
        monkeypatch.setenv("DEBUG", "")
        monkeypatch.setenv("HARP_DEBUG", "")
        assert self._reload_harp_debug() is False

    def test_harp_debug_takes_precedence_over_debug(self, monkeypatch):
        monkeypatch.setenv("DEBUG", "")
        monkeypatch.setenv("HARP_DEBUG", "1")
        assert self._reload_harp_debug() is True

    def test_reload_leaves_sys_modules_untouched(self, monkeypatch):
        """Reloading must not leak fresh module objects into the interpreter, which would break
        isinstance checks in every test module imported before this one."""
        monkeypatch.delenv("DEBUG", raising=False)
        monkeypatch.delenv("HARP_DEBUG", raising=False)

        import harp.http.responses  # noqa: F401

        before = _harp_modules()
        self._reload_harp_debug()

        assert _harp_modules() == before
