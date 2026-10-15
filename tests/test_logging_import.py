import subprocess
import sys
import textwrap


def _run(code: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-I", "-c", textwrap.dedent(code)], capture_output=True, text=True)


def test_import_harp_keeps_host_loggers_enabled():
    result = _run(
        """
        import logging

        records = []

        class Collect(logging.Handler):
            def emit(self, record):
                records.append(record.getMessage())

        app = logging.getLogger("host.app")
        app.addHandler(Collect())
        app.setLevel(logging.INFO)
        app.info("before")

        import harp

        app.info("after")
        assert records == ["before", "after"], records
        """
    )
    assert result.returncode == 0, result.stderr


def test_import_harp_configures_neither_stdlib_nor_structlog():
    result = _run(
        """
        import logging
        import structlog

        root_handlers = list(logging.getLogger().handlers)
        was_configured = structlog.is_configured()

        import harp

        assert logging.getLogger().handlers == root_handlers
        assert structlog.is_configured() == was_configured
        """
    )
    assert result.returncode == 0, result.stderr


def test_entrypoint_configures_logging():
    result = _run(
        """
        import logging
        import structlog

        from click.testing import CliRunner
        from harp.commandline import entrypoint

        assert not structlog.is_configured()
        CliRunner().invoke(entrypoint, ["version"])
        assert structlog.is_configured()
        assert logging.getLogger().handlers
        """
    )
    assert result.returncode == 0, result.stderr
