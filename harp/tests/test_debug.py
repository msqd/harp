import sys

import pytest
from structlog.testing import capture_logs


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

    def _debug_with(self, monkeypatch, **env):
        for name in ("DEBUG", "HARP_DEBUG"):
            monkeypatch.delenv(name, raising=False)
        for name, value in env.items():
            monkeypatch.setenv(name, value)
        return self._reload_harp_debug()

    def test_debug_is_false_when_no_env_vars_set(self, monkeypatch):
        assert self._debug_with(monkeypatch) is False

    @pytest.mark.parametrize("value", ["1", "true", "yes", "on", "TRUE", "Yes", "On"])
    def test_harp_debug_truthy_values_enable(self, monkeypatch, value):
        assert self._debug_with(monkeypatch, HARP_DEBUG=value) is True

    @pytest.mark.parametrize("value", ["0", "false", "no", "off", "FALSE", "Off", ""])
    def test_harp_debug_falsy_values_disable(self, monkeypatch, value):
        assert self._debug_with(monkeypatch, HARP_DEBUG=value) is False

    @pytest.mark.parametrize("value", ["maybe", "2", "enabled"])
    def test_harp_debug_other_values_fail_at_startup(self, monkeypatch, value):
        with pytest.raises(ValueError, match="HARP_DEBUG"):
            self._debug_with(monkeypatch, HARP_DEBUG=value)

    def test_harp_debug_takes_precedence_over_debug(self, monkeypatch):
        assert self._debug_with(monkeypatch, HARP_DEBUG="0", DEBUG="1") is False

    def test_harp_debug_set_does_not_warn_about_debug(self, monkeypatch):
        with capture_logs() as logs:
            self._debug_with(monkeypatch, HARP_DEBUG="1", DEBUG="1")
        assert not [entry for entry in logs if entry["log_level"] == "warning"]

    def test_generic_debug_still_enables_with_deprecation_warning(self, monkeypatch):
        with capture_logs() as logs:
            assert self._debug_with(monkeypatch, DEBUG="1") is True
        warnings = [entry for entry in logs if entry["log_level"] == "warning"]
        assert len(warnings) == 1
        assert "HARP_DEBUG" in warnings[0]["event"]

    @pytest.mark.parametrize("value", ["0", "false", "no", "off", ""])
    def test_generic_debug_falsy_values_do_not_enable(self, monkeypatch, value):
        assert self._debug_with(monkeypatch, DEBUG=value) is False

    def test_reload_leaves_sys_modules_untouched(self, monkeypatch):
        """Reloading must not leak fresh module objects into the interpreter, which would break
        isinstance checks in every test module imported before this one."""
        monkeypatch.delenv("DEBUG", raising=False)
        monkeypatch.delenv("HARP_DEBUG", raising=False)

        import harp.http.responses  # noqa: F401

        before = _harp_modules()
        self._reload_harp_debug()

        assert _harp_modules() == before
