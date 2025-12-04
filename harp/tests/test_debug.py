import sys


class TestDebugFlag:
    """Tests for the harp.DEBUG constant."""

    def _reload_harp_debug(self):
        """Reload harp module to re-evaluate DEBUG constant."""
        # Remove harp from sys.modules to force re-import
        modules_to_remove = [key for key in sys.modules if key == "harp" or key.startswith("harp.")]
        for mod in modules_to_remove:
            del sys.modules[mod]
        import harp

        return harp.DEBUG

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
