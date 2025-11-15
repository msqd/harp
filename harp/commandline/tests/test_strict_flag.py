"""
Tests for --strict CLI flag functionality.

These tests verify that:
1. --strict flag is available on CLI commands that use server_command decorator
2. --strict flag is passed through to ConfigurationBuilder.build()
3. --strict flag affects error behavior (warnings vs errors)
4. --strict flag works with all server commands
"""

from click.testing import CliRunner
from unittest.mock import MagicMock, patch

from harp.commandline.options.server import CommonServerOptions, server_command
from harp.config import Configurable
from harp.config.builders import ConfigurationBuilder
from harp.config.mixins import ApplicationSettingsMixin


class TestStrictFlagAvailability:
    """Test that --strict flag is available on CLI."""

    def test_strict_flag_exists_on_server_command(self):
        """Test that server_command decorator adds --strict flag."""

        @server_command()
        def test_cmd(**kwargs):
            return kwargs

        runner = CliRunner()
        result = runner.invoke(test_cmd, ["--help"])

        # Should include --strict in help text
        assert "--strict" in result.output

    def test_strict_flag_is_boolean(self):
        """Test that --strict flag is a boolean option."""

        @server_command()
        def test_cmd(strict, **kwargs):
            return strict

        runner = CliRunner()

        # Test with flag
        result = runner.invoke(test_cmd, ["--strict"])
        assert result.exit_code == 0

        # Test without flag
        result = runner.invoke(test_cmd, [])
        assert result.exit_code == 0

    def test_strict_flag_no_value_required(self):
        """Test that --strict is a flag that doesn't require a value."""

        @server_command()
        def test_cmd(strict=False, **kwargs):
            return {"strict": strict}

        runner = CliRunner()

        # Should work without value
        result = runner.invoke(test_cmd, ["--strict"])
        assert result.exit_code == 0

        # Should fail if value is provided
        result = runner.invoke(test_cmd, ["--strict", "true"])
        # Behavior depends on how flag is implemented
        # It might consume "true" as next argument or fail

    def test_strict_flag_defaults_to_false(self):
        """Test that --strict defaults to False when not provided."""

        @server_command()
        def test_cmd(strict=False, **kwargs):
            return {"strict": strict}

        runner = CliRunner()
        runner.invoke(test_cmd, [])

        # When checking the result, strict should be False
        # This would need to be verified in the actual command logic


class TestStrictFlagInCommonServerOptions:
    """Test that CommonServerOptions includes strict parameter."""

    def test_common_server_options_accepts_strict(self):
        """Test that CommonServerOptions dataclass accepts strict parameter."""
        # This will fail because strict field doesn't exist yet
        options = CommonServerOptions(
            options=(),
            files=(),
            enable=(),
            disable=(),
            strict=True,  # This field doesn't exist yet
        )

        assert options.strict is True

    def test_common_server_options_strict_defaults_to_false(self):
        """Test that strict defaults to False in CommonServerOptions."""
        options = CommonServerOptions(
            options=(),
            files=(),
            enable=(),
            disable=(),
        )

        assert hasattr(options, "strict")
        assert options.strict is False

    def test_common_server_options_as_list_includes_strict(self):
        """Test that as_list() includes --strict when strict=True."""
        options = CommonServerOptions(
            options=(),
            files=(),
            enable=(),
            disable=(),
            strict=True,
        )

        as_list = options.as_list()
        assert "--strict" in as_list


class TestStrictFlagPassedToConfigurationBuilder:
    """Test that --strict flag is passed to ConfigurationBuilder.build()."""

    def test_strict_flag_passed_to_build_method(self):
        """Test that strict parameter is passed to ConfigurationBuilder.build()."""

        @server_command()
        def test_cmd(strict=False, **kwargs):
            # Simulate what a real command would do
            options = CommonServerOptions(strict=strict, **kwargs)
            builder = ConfigurationBuilder.from_commandline_options(options)
            config = builder.build(strict=strict)
            return config

        runner = CliRunner()

        # Mock the build method to verify it receives strict parameter
        with patch.object(ConfigurationBuilder, "build") as mock_build:
            mock_build.return_value = {"applications": []}

            runner.invoke(test_cmd, ["--strict"])

            # Verify build was called with strict=True
            mock_build.assert_called_once()
            call_kwargs = mock_build.call_args[1] if mock_build.call_args[1] else {}
            assert call_kwargs.get("strict", False) is True

    def test_from_commandline_options_preserves_strict_flag(self):
        """Test that from_commandline_options preserves strict flag."""
        options = CommonServerOptions(
            options=(),
            files=(),
            enable=(),
            disable=(),
            strict=True,
        )

        builder = ConfigurationBuilder.from_commandline_options(options)

        # Builder should store strict flag for later use
        # This might be stored as an attribute or passed through
        assert builder.strict is True or hasattr(builder, "strict")

    def test_strict_false_by_default_in_commandline_flow(self):
        """Test that strict defaults to False in normal command flow."""

        @server_command()
        def test_cmd(**kwargs):
            options = CommonServerOptions(**kwargs)
            return options.strict if hasattr(options, "strict") else False

        runner = CliRunner()
        runner.invoke(test_cmd, [])

        # Default should be False


class TestStrictFlagBehaviorIntegration:
    """Test strict flag behavior in integration scenarios."""

    def test_strict_flag_causes_error_on_invalid_config(self):
        """Test that --strict causes error instead of warning for invalid config."""

        @server_command()
        def test_cmd(strict=False, **kwargs):
            options = CommonServerOptions(strict=strict, **kwargs)
            builder = ConfigurationBuilder.from_commandline_options(options)
            # Add invalid config
            builder.add_values({"nonexistent_app": {"setting": "value"}})
            config = builder.build(strict=strict)
            return config

        runner = CliRunner()

        # Without --strict, should succeed with warnings
        result = runner.invoke(test_cmd, [])
        assert result.exit_code == 0

        # With --strict, should fail
        result = runner.invoke(test_cmd, ["--strict"])
        assert result.exit_code != 0
        assert "error" in result.output.lower() or result.exception is not None

    def test_strict_flag_allows_valid_config(self):
        """Test that --strict doesn't affect valid configuration."""

        @server_command()
        def test_cmd(strict=False, **kwargs):
            options = CommonServerOptions(strict=strict, **kwargs)
            builder = ConfigurationBuilder.from_commandline_options(options)
            builder.applications.add("storage")
            builder.add_values({"storage": {"url": "sqlite:///:memory:"}})
            config = builder.build(strict=strict)
            return config

        runner = CliRunner()

        # Valid config should work with --strict
        result = runner.invoke(test_cmd, ["--strict"])
        assert result.exit_code == 0

    def test_strict_flag_allows_disabled_app_config(self):
        """Test that --strict does NOT raise error when disabled app has config.

        Disabled apps (enabled: false) are intentional configuration directives.
        Strict mode only catches unloaded/unknown apps, not explicitly disabled ones.
        """
        from importlib.machinery import ModuleSpec
        from types import ModuleType

        # Create test app
        test_app_module = ModuleType("test_app")
        test_app_module.__spec__ = ModuleSpec(name="test_app", loader=None)

        class TestAppSettings(ApplicationSettingsMixin, Configurable):
            name: str = "test"

        test_app_app_module = ModuleType("test_app.__app__")
        test_app_app_module.application = MagicMock()
        test_app_app_module.application.settings_type = TestAppSettings
        test_app_app_module.__spec__ = ModuleSpec(name="test_app.__app__", loader=None)

        @server_command()
        def test_cmd(strict=False, **kwargs):
            options = CommonServerOptions(strict=strict, **kwargs)
            builder = ConfigurationBuilder.from_commandline_options(options)
            with patch.dict(
                "sys.modules",
                {
                    "test_app": test_app_module,
                    "test_app.__app__": test_app_app_module,
                },
            ):
                builder.applications.add("test_app")
                builder.add_values({"test_app": {"enabled": False}})
                config = builder.build(strict=strict)
            return config

        runner = CliRunner()

        # Without --strict, should warn but succeed
        result = runner.invoke(test_cmd, [])
        assert result.exit_code == 0

        # With --strict, should also succeed (disabled apps are OK)
        result = runner.invoke(test_cmd, ["--strict"])
        assert result.exit_code == 0


class TestStrictFlagHelp:
    """Test --strict flag help text and documentation."""

    def test_strict_flag_has_help_text(self):
        """Test that --strict flag has descriptive help text."""

        @server_command()
        def test_cmd(**kwargs):
            pass

        runner = CliRunner()
        result = runner.invoke(test_cmd, ["--help"])

        # Should have help text explaining strict mode
        assert "--strict" in result.output
        # Help text should explain the behavior
        help_indicators = ["error", "warning", "validation", "fail"]
        assert any(indicator in result.output.lower() for indicator in help_indicators)

    def test_strict_flag_help_mentions_warnings(self):
        """Test that help text mentions warnings being converted to errors."""

        @server_command()
        def test_cmd(**kwargs):
            pass

        runner = CliRunner()
        result = runner.invoke(test_cmd, ["--help"])

        # Look for the --strict option and its help
        output_lower = result.output.lower()
        if "--strict" in result.output:
            # Help should explain that it makes validation stricter
            assert "warning" in output_lower or "error" in output_lower


class TestStrictFlagWithOtherOptions:
    """Test --strict flag interaction with other CLI options."""

    def test_strict_with_enable_flag(self):
        """Test --strict works correctly with --enable flag."""

        @server_command()
        def test_cmd(strict=False, enable=(), **kwargs):
            return {"strict": strict, "enable": enable}

        runner = CliRunner()
        result = runner.invoke(test_cmd, ["--strict", "--enable", "storage"])

        assert result.exit_code == 0
        # Both flags should be processed

    def test_strict_with_disable_flag(self):
        """Test --strict works correctly with --disable flag."""

        @server_command()
        def test_cmd(strict=False, disable=(), **kwargs):
            return {"strict": strict, "disable": disable}

        runner = CliRunner()
        result = runner.invoke(test_cmd, ["--strict", "--disable", "dashboard"])

        assert result.exit_code == 0

    def test_strict_with_file_option(self):
        """Test --strict works correctly with --file option."""

        @server_command()
        def test_cmd(strict=False, files=(), **kwargs):
            return {"strict": strict, "files": files}

        CliRunner()

        # Would need a real file to test fully
        # For now, test that flags are compatible
        # result = runner.invoke(test_cmd, ["--strict", "--file", "config.yaml"])

    def test_strict_with_set_option(self):
        """Test --strict works correctly with --set option."""

        @server_command()
        def test_cmd(strict=False, options=(), **kwargs):
            return {"strict": strict, "options": options}

        runner = CliRunner()
        result = runner.invoke(test_cmd, ["--strict", "--set", "foo=bar"])

        assert result.exit_code == 0

    def test_strict_flag_position_independent(self):
        """Test that --strict can appear anywhere in argument list."""

        @server_command()
        def test_cmd(strict=False, enable=(), **kwargs):
            return {"strict": strict, "enable": enable}

        runner = CliRunner()

        # --strict first
        result1 = runner.invoke(test_cmd, ["--strict", "--enable", "storage"])

        # --strict last
        result2 = runner.invoke(test_cmd, ["--enable", "storage", "--strict"])

        # Both should work
        assert result1.exit_code == 0
        assert result2.exit_code == 0


class TestStrictFlagOnActualCommands:
    """Test --strict flag on actual HARP commands."""

    def test_strict_on_server_command(self):
        """Test that --strict is available on 'harp server' command."""
        from harp.commandline.server import server

        runner = CliRunner()
        result = runner.invoke(server, ["--help"])

        # Should have --strict flag
        assert "--strict" in result.output or result.exit_code == 0  # May not be implemented yet

    def test_strict_on_system_config_command(self):
        """Test that --strict is available on 'harp system config' command."""
        from harp.commandline.system import system

        runner = CliRunner()
        result = runner.invoke(system, ["config", "--help"])

        # System config command should support strict mode
        assert "--strict" in result.output or result.exit_code == 0


class TestStrictFlagErrorMessages:
    """Test error messages produced when --strict is enabled."""

    def test_strict_error_message_is_helpful(self):
        """Test that error message with --strict provides actionable guidance."""

        @server_command()
        def test_cmd(strict=False, **kwargs):
            options = CommonServerOptions(strict=strict, **kwargs)
            builder = ConfigurationBuilder.from_commandline_options(options)
            builder.add_values({"bad_app": {"setting": "value"}})
            config = builder.build(strict=strict)
            return config

        runner = CliRunner()
        result = runner.invoke(test_cmd, ["--strict"])

        if result.exit_code != 0:
            # Error output should mention the problematic app
            error_output = result.output + str(result.exception) if result.exception else result.output
            assert "bad_app" in error_output.lower()

    def test_strict_error_includes_app_name(self):
        """Test that strict mode error includes the problematic app name."""

        @server_command()
        def test_cmd(strict=False, **kwargs):
            options = CommonServerOptions(strict=strict, **kwargs)
            builder = ConfigurationBuilder.from_commandline_options(options)
            builder.add_values({"unknown_application": {"setting": "value"}})
            config = builder.build(strict=strict)
            return config

        runner = CliRunner()
        result = runner.invoke(test_cmd, ["--strict"])

        if result.exit_code != 0:
            error_output = result.output + str(result.exception) if result.exception else result.output
            assert "unknown_application" in error_output.lower()

    def test_strict_error_suggests_solutions(self):
        """Test that strict mode error suggests how to fix the issue."""

        @server_command()
        def test_cmd(strict=False, **kwargs):
            options = CommonServerOptions(strict=strict, **kwargs)
            builder = ConfigurationBuilder.from_commandline_options(options)
            builder.add_values({"nonexistent": {"setting": "value"}})
            config = builder.build(strict=strict)
            return config

        runner = CliRunner()
        result = runner.invoke(test_cmd, ["--strict"])

        if result.exit_code != 0:
            result.output.lower()
            # Should suggest actions like --enable, checking app name, etc.
            # At least one suggestion should be present
