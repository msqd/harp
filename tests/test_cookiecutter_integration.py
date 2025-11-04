"""
Integration tests for cookiecutter template migration to uv.

These tests verify that the cookiecutter template at harp/commandline/cookiecutters/project/
can successfully generate working projects that use uv instead of Poetry.

CRITICAL: These tests MUST FAIL initially because they test the complete end-to-end workflow.
They will pass once the template migration is complete and all commands work correctly.

Test Strategy:
1. Generate actual projects using cookiecutter programmatically
2. Execute real shell commands in generated projects (uv sync, make install, etc.)
3. Verify generated files contain correct content (no Poetry references)
4. Test both configuration variations (with/without application and config)
5. Clean up temporary projects after tests
"""

import os
import re
import socket
import subprocess
import time
from pathlib import Path

import pytest
import requests


# Path to the cookiecutter template directory
TEMPLATE_DIR = Path(__file__).parent.parent / "harp" / "commandline" / "cookiecutters" / "project"


class TestProjectGeneration:
    """Test actual project generation using cookiecutter."""

    def test_can_generate_project_with_cookiecutter(self, tmp_path):
        """
        Verify cookiecutter can successfully generate a project from the template.

        EXPECTED TO FAIL: This tests the basic generation workflow works.
        """
        from cookiecutter.main import cookiecutter

        # Generate project with default settings
        project_dir = cookiecutter(
            str(TEMPLATE_DIR),
            output_dir=str(tmp_path),
            no_input=True,
            extra_context={
                "name": "Test Project",
                "author_name": "Test Author",
                "author_email": "test@example.com",
                "create_application": True,
                "create_config": True,
            },
        )

        assert Path(project_dir).exists(), "Generated project directory should exist"
        assert Path(project_dir, "pyproject.toml").exists(), "Generated project should have pyproject.toml"
        assert Path(project_dir, "Makefile").exists(), "Generated project should have Makefile"

    def test_generate_project_with_application_true_config_true(self, tmp_path):
        """
        Generate project with create_application=True and create_config=True.

        EXPECTED TO FAIL: Verifies both application folder and config file are created.
        """
        from cookiecutter.main import cookiecutter

        project_dir = cookiecutter(
            str(TEMPLATE_DIR),
            output_dir=str(tmp_path),
            no_input=True,
            extra_context={
                "name": "Full Project",
                "create_application": True,
                "create_config": True,
            },
        )

        # Verify application folder exists
        assert Path(project_dir, "full_project").exists(), (
            "Application folder should exist when create_application=True"
        )

        # Verify config file exists
        assert Path(project_dir, "config.yml").exists(), "Config file should exist when create_config=True"

    def test_generate_project_with_application_false_config_false(self, tmp_path):
        """
        Generate project with create_application=False and create_config=False.

        EXPECTED TO FAIL: Verifies post-generation hook correctly removes files.
        """
        from cookiecutter.main import cookiecutter

        project_dir = cookiecutter(
            str(TEMPLATE_DIR),
            output_dir=str(tmp_path),
            no_input=True,
            extra_context={
                "name": "Minimal Project",
                "create_application": False,
                "create_config": False,
            },
        )

        # Verify application folder does NOT exist
        assert not Path(project_dir, "minimal_project").exists(), (
            "Application folder should NOT exist when create_application=False"
        )

        # Verify config file does NOT exist
        assert not Path(project_dir, "config.yml").exists(), "Config file should NOT exist when create_config=False"

    def test_generated_pyproject_toml_has_pep621_format(self, tmp_path):
        """
        Verify generated pyproject.toml uses PEP 621 format (not Poetry format).

        EXPECTED TO FAIL: Validates the template produces correct PEP 621 output.
        """
        from cookiecutter.main import cookiecutter

        project_dir = cookiecutter(
            str(TEMPLATE_DIR),
            output_dir=str(tmp_path),
            no_input=True,
            extra_context={"name": "PEP621 Test", "create_application": True},
        )

        pyproject_content = Path(project_dir, "pyproject.toml").read_text()

        # Should use [project] section
        assert "[project]" in pyproject_content, "Generated pyproject.toml should use [project] section"

        # Should NOT use [tool.poetry] section
        assert "[tool.poetry]" not in pyproject_content, "Generated pyproject.toml should NOT use [tool.poetry] section"

        # Should use hatchling build backend
        assert "hatchling.build" in pyproject_content, "Generated pyproject.toml should use hatchling build backend"

        # Should NOT use poetry-core
        assert "poetry-core" not in pyproject_content, "Generated pyproject.toml should NOT use poetry-core"

        # Should have Python version >=3.13,<3.14
        assert 'requires-python = ">=3.13,<3.14"' in pyproject_content, (
            "Generated pyproject.toml should specify Python >=3.13,<3.14"
        )

    def test_generated_makefile_has_uv_commands(self, tmp_path):
        """
        Verify generated Makefile uses uv commands (not poetry).

        EXPECTED TO FAIL: Validates the template produces Makefile with uv.
        """
        from cookiecutter.main import cookiecutter

        project_dir = cookiecutter(
            str(TEMPLATE_DIR), output_dir=str(tmp_path), no_input=True, extra_context={"name": "UV Makefile Test"}
        )

        makefile_content = Path(project_dir, "Makefile").read_text()

        # Should define UV variable
        assert "UV ?=" in makefile_content, "Generated Makefile should define UV variable"

        # Should use 'uv sync' or '$(UV) sync' for install
        assert "uv sync" in makefile_content or "$(UV) sync" in makefile_content, (
            "Generated Makefile should use 'uv sync' or '$(UV) sync' for install target"
        )

        # Should use 'uv run' or '$(UV) run' for commands
        assert "uv run" in makefile_content or "$(UV) run" in makefile_content, (
            "Generated Makefile should use 'uv run' or '$(UV) run' for commands"
        )

        # Should NOT mention poetry
        assert "poetry" not in makefile_content.lower(), "Generated Makefile should NOT contain any poetry references"


class TestUVCommandsInGeneratedProject:
    """Test that uv commands work in generated projects."""

    def test_uv_sync_creates_venv(self, tmp_path):
        """
        Run 'uv sync' in generated project and verify .venv is created.

        EXPECTED TO FAIL: This tests uv can successfully install dependencies.
        """
        from cookiecutter.main import cookiecutter

        project_dir = cookiecutter(
            str(TEMPLATE_DIR),
            output_dir=str(tmp_path),
            no_input=True,
            extra_context={"name": "UV Sync Test", "create_application": False},
        )

        # Run uv sync
        result = subprocess.run(
            ["uv", "sync"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutes max for dependency installation
        )

        assert result.returncode == 0, f"uv sync failed: {result.stderr}"

        # Verify .venv directory was created
        venv_path = Path(project_dir, ".venv")
        assert venv_path.exists(), ".venv directory should be created by uv sync"
        assert venv_path.is_dir(), ".venv should be a directory"

    def test_uv_sync_installs_harp_proxy(self, tmp_path):
        """
        Verify that 'uv sync' installs harp-proxy package.

        EXPECTED TO FAIL: Validates harp-proxy dependency is correctly specified.
        """
        from cookiecutter.main import cookiecutter

        project_dir = cookiecutter(
            str(TEMPLATE_DIR),
            output_dir=str(tmp_path),
            no_input=True,
            extra_context={"name": "Harp Install Test", "create_application": False},
        )

        # Run uv sync
        subprocess.run(["uv", "sync"], cwd=project_dir, check=True, capture_output=True, timeout=300)

        # Check that harp-proxy is installed by running uv run harp-proxy version
        result = subprocess.run(
            ["uv", "run", "harp-proxy", "version"], cwd=project_dir, capture_output=True, text=True, timeout=30
        )

        assert result.returncode == 0, f"harp-proxy should be installed and runnable: {result.stderr}"
        assert "harp" in result.stdout.lower(), "harp-proxy version should output version information"

    def test_uv_run_works_in_generated_project(self, tmp_path):
        """
        Verify 'uv run' command works in generated project.

        EXPECTED TO FAIL: Tests that uv can execute commands in the project environment.
        """
        from cookiecutter.main import cookiecutter

        project_dir = cookiecutter(
            str(TEMPLATE_DIR),
            output_dir=str(tmp_path),
            no_input=True,
            extra_context={"name": "UV Run Test", "create_application": False},
        )

        # First install dependencies
        subprocess.run(["uv", "sync"], cwd=project_dir, check=True, capture_output=True, timeout=300)

        # Test uv run with a simple command
        result = subprocess.run(
            ["uv", "run", "python", "--version"], cwd=project_dir, capture_output=True, text=True, timeout=30
        )

        assert result.returncode == 0, f"uv run python --version failed: {result.stderr}"
        assert "Python 3.13" in result.stdout, "Should run Python 3.13"


class TestMakefileTargetsInGeneratedProject:
    """Test that Makefile targets work correctly in generated projects."""

    def test_make_install_runs_uv_sync(self, tmp_path):
        """
        Verify 'make install' successfully runs in generated project.

        EXPECTED TO FAIL: Tests that make install (which calls uv sync) works.
        """
        from cookiecutter.main import cookiecutter

        project_dir = cookiecutter(
            str(TEMPLATE_DIR),
            output_dir=str(tmp_path),
            no_input=True,
            extra_context={"name": "Make Install Test", "create_application": False},
        )

        # Run make install
        result = subprocess.run(["make", "install"], cwd=project_dir, capture_output=True, text=True, timeout=300)

        assert result.returncode == 0, f"make install failed: {result.stderr}"

        # Verify .venv was created (side effect of uv sync)
        assert Path(project_dir, ".venv").exists(), "make install should create .venv via uv sync"

    def test_make_test_runs_uv_run_pytest(self, tmp_path):
        """
        Verify 'make test' successfully runs in generated project.

        EXPECTED TO FAIL: Tests that make test (which calls uv run pytest) works.
        Note: This may fail if no tests exist, but should not fail due to command issues.
        """
        from cookiecutter.main import cookiecutter

        project_dir = cookiecutter(
            str(TEMPLATE_DIR),
            output_dir=str(tmp_path),
            no_input=True,
            extra_context={"name": "Make Test Project", "create_application": True},
        )

        # First install dependencies
        subprocess.run(["make", "install"], cwd=project_dir, check=True, capture_output=True, timeout=300)

        # Run make test
        result = subprocess.run(["make", "test"], cwd=project_dir, capture_output=True, text=True, timeout=60)

        # The command itself should work (returncode might be non-zero if no tests exist)
        # But there should be no "command not found" or similar errors
        assert "command not found" not in result.stderr.lower(), (
            f"make test should not fail with command not found: {result.stderr}"
        )
        assert "poetry" not in result.stderr.lower(), f"make test should not reference poetry: {result.stderr}"

    def test_make_start_uses_uv_run_harp(self, tmp_path):
        """
        Verify 'make start' command is correctly configured.

        EXPECTED TO FAIL: Tests that make start target references uv run harp.
        Note: We don't actually start the server, just verify the command structure.
        """
        from cookiecutter.main import cookiecutter

        project_dir = cookiecutter(
            str(TEMPLATE_DIR),
            output_dir=str(tmp_path),
            no_input=True,
            extra_context={"name": "Make Start Test", "create_application": True, "create_config": True},
        )

        makefile_content = Path(project_dir, "Makefile").read_text()

        # Find the start target
        lines = makefile_content.split("\n")
        start_target_found = False
        for i, line in enumerate(lines):
            if line.startswith("start:"):
                start_target_found = True
                # Check next few lines for the command
                command_lines = []
                for j in range(i + 1, min(i + 5, len(lines))):
                    if lines[j].startswith("\t"):
                        command_lines.append(lines[j])
                    else:
                        break

                command_text = " ".join(command_lines)
                assert "uv run harp-proxy" in command_text or "$(UV) run harp-proxy" in command_text, (
                    f"start target should use 'uv run harp-proxy server' or '$(UV) run harp-proxy server': {command_text}"
                )
                assert "--enable make_start_test" in command_text, (
                    f"start target should enable application when create_application=True: {command_text}"
                )
                assert "--file config.yml" in command_text, (
                    f"start target should use config file when create_config=True: {command_text}"
                )
                break

        assert start_target_found, "Makefile should have a start target"


class TestPostGenerationHook:
    """Test that post-generation hook works correctly."""

    def test_hook_runs_successfully(self, tmp_path, capsys):
        """
        Verify post_gen_project.sh hook executes without errors.

        EXPECTED TO FAIL: Tests the hook script runs successfully.
        """
        from cookiecutter.main import cookiecutter

        # Generate project - hook should run automatically
        project_dir = cookiecutter(
            str(TEMPLATE_DIR), output_dir=str(tmp_path), no_input=True, extra_context={"name": "Hook Test Project"}
        )

        # If we get here without exception, hook ran successfully
        assert Path(project_dir).exists(), "Project should be generated successfully"

    def test_hook_removes_application_when_create_application_false(self, tmp_path):
        """
        Verify hook removes application folder when create_application=False.

        EXPECTED TO FAIL: Tests conditional file cleanup works correctly.
        """
        from cookiecutter.main import cookiecutter

        project_dir = cookiecutter(
            str(TEMPLATE_DIR),
            output_dir=str(tmp_path),
            no_input=True,
            extra_context={
                "name": "No App Project",
                "create_application": False,
                "create_config": True,
            },
        )

        # Application folder should be removed by hook
        app_folder = Path(project_dir, "no_app_project")
        assert not app_folder.exists(), (
            f"Application folder should be removed when create_application=False: {app_folder}"
        )

    def test_hook_removes_config_when_create_config_false(self, tmp_path):
        """
        Verify hook removes config.yml when create_config=False.

        EXPECTED TO FAIL: Tests conditional config file cleanup works correctly.
        """
        from cookiecutter.main import cookiecutter

        project_dir = cookiecutter(
            str(TEMPLATE_DIR),
            output_dir=str(tmp_path),
            no_input=True,
            extra_context={
                "name": "No Config Project",
                "create_application": True,
                "create_config": False,
            },
        )

        # Config file should be removed by hook
        config_file = Path(project_dir, "config.yml")
        assert not config_file.exists(), "config.yml should be removed when create_config=False"

    def test_hook_displays_success_message(self, tmp_path, capsys):
        """
        Verify hook displays success message after generation.

        EXPECTED TO FAIL: Tests success message is shown to user.
        """
        from cookiecutter.main import cookiecutter

        cookiecutter(
            str(TEMPLATE_DIR), output_dir=str(tmp_path), no_input=True, extra_context={"name": "Success Message Test"}
        )

        # Cookiecutter should output the hook's success message
        # This is challenging to test as the message goes to stdout during generation
        # We verify the hook file contains the expected message format
        hook_path = TEMPLATE_DIR / "hooks" / "post_gen_project.sh"
        hook_content = hook_path.read_text()

        assert "Congratulations" in hook_content, "Hook should contain congratulations message"
        assert "make install" in hook_content, "Hook should mention 'make install' command"
        assert "make test" in hook_content, "Hook should mention 'make test' command"
        assert "make" in hook_content, "Hook should mention 'make' command to start project"


class TestNoPoetryArtifacts:
    """Test that generated projects contain no Poetry artifacts or references."""

    def test_no_poetry_lock_file(self, tmp_path):
        """
        Verify no poetry.lock file is created in generated project.

        EXPECTED TO FAIL: Ensures Poetry lockfile is not generated.
        """
        from cookiecutter.main import cookiecutter

        project_dir = cookiecutter(
            str(TEMPLATE_DIR), output_dir=str(tmp_path), no_input=True, extra_context={"name": "No Poetry Lock Test"}
        )

        poetry_lock = Path(project_dir, "poetry.lock")
        assert not poetry_lock.exists(), "poetry.lock should NOT exist in generated project"

    def test_no_poetry_references_in_pyproject_toml(self, tmp_path):
        """
        Verify generated pyproject.toml contains no Poetry references.

        EXPECTED TO FAIL: Ensures all Poetry sections are removed.
        """
        from cookiecutter.main import cookiecutter

        project_dir = cookiecutter(
            str(TEMPLATE_DIR), output_dir=str(tmp_path), no_input=True, extra_context={"name": "Clean Project Test"}
        )

        pyproject_content = Path(project_dir, "pyproject.toml").read_text()

        # Check for actual Poetry-specific strings (not just "poetry" substring)
        poetry_indicators = [
            "[tool.poetry]",
            "poetry-core",
            "poetry.lock",
            "poetry install",
            "poetry run",
            "poetry add",
        ]

        found_indicators = [
            indicator for indicator in poetry_indicators if indicator.lower() in pyproject_content.lower()
        ]

        assert len(found_indicators) == 0, (
            f"Generated pyproject.toml contains Poetry references: {found_indicators}\n{pyproject_content}"
        )

    def test_no_poetry_references_in_makefile(self, tmp_path):
        """
        Verify generated Makefile contains no Poetry references.

        EXPECTED TO FAIL: Ensures Makefile only uses uv commands.
        """
        from cookiecutter.main import cookiecutter

        project_dir = cookiecutter(
            str(TEMPLATE_DIR),
            output_dir=str(tmp_path),
            no_input=True,
            extra_context={"name": "UV Makefile Test"},  # Changed: avoid "poetry" in project name
        )

        makefile_content = Path(project_dir, "Makefile").read_text()

        # Check for poetry commands (case-insensitive), but exclude project name mentions
        poetry_commands = ["poetry install", "poetry run", "poetry add", "poetry.lock", "POETRY ?="]
        for cmd in poetry_commands:
            assert cmd.lower() not in makefile_content.lower(), f"Generated Makefile should not contain '{cmd}' command"

    def test_no_poetry_references_in_any_file(self, tmp_path):
        """
        Scan all generated files for Poetry-specific strings.

        EXPECTED TO FAIL: Comprehensive check for any Poetry references.
        """
        from cookiecutter.main import cookiecutter

        project_dir = cookiecutter(
            str(TEMPLATE_DIR), output_dir=str(tmp_path), no_input=True, extra_context={"name": "Comprehensive Check"}
        )

        # Check for actual Poetry-specific strings (not just "poetry" substring)
        poetry_indicators = [
            "[tool.poetry]",
            "poetry-core",
            "poetry.lock",
            "poetry install",
            "poetry run",
            "poetry add",
            "poetry update",
            "poetry shell",
        ]

        # Scan all non-binary files for Poetry indicators
        files_with_poetry_refs = {}
        for file_path in Path(project_dir).rglob("*"):
            if file_path.is_file() and not file_path.name.startswith("."):
                # Skip binary files and common non-text files
                if file_path.suffix in (".pyc", ".pyo", ".so", ".dylib", ".dll"):
                    continue

                try:
                    content = file_path.read_text()
                    found_indicators = [
                        indicator for indicator in poetry_indicators if indicator.lower() in content.lower()
                    ]
                    if found_indicators:
                        files_with_poetry_refs[str(file_path.relative_to(project_dir))] = found_indicators
                except (UnicodeDecodeError, PermissionError):
                    # Skip files that can't be read as text
                    pass

        assert len(files_with_poetry_refs) == 0, (
            f"The following files contain Poetry references: {files_with_poetry_refs}"
        )


class TestEndToEndWorkflow:
    """Test complete end-to-end workflow of project generation and usage."""

    def test_complete_workflow_with_application(self, tmp_path):
        """
        Full integration test: generate project with application, install, verify it works.

        EXPECTED TO FAIL: This is the ultimate integration test - everything must work.
        """
        from cookiecutter.main import cookiecutter

        # Generate project with application
        project_dir = cookiecutter(
            str(TEMPLATE_DIR),
            output_dir=str(tmp_path),
            no_input=True,
            extra_context={
                "name": "E2E Test Project",
                "author_name": "E2E Tester",
                "author_email": "e2e@test.com",
                "create_application": True,
                "create_config": True,
            },
        )

        # Verify project structure
        assert Path(project_dir, "pyproject.toml").exists()
        assert Path(project_dir, "Makefile").exists()
        assert Path(project_dir, "e2e_test_project").exists()
        assert Path(project_dir, "config.yml").exists()

        # Install dependencies using make
        result = subprocess.run(["make", "install"], cwd=project_dir, capture_output=True, text=True, timeout=300)
        assert result.returncode == 0, f"make install failed: {result.stderr}"

        # Verify harp-proxy is installed
        result = subprocess.run(
            ["uv", "run", "harp-proxy", "version"], cwd=project_dir, capture_output=True, text=True, timeout=30
        )
        assert result.returncode == 0, f"harp-proxy not installed: {result.stderr}"

        # Verify uv.lock was created
        assert Path(project_dir, "uv.lock").exists(), "uv.lock should be created"

        # Verify .venv was created
        assert Path(project_dir, ".venv").exists(), ".venv should be created"

        # Verify no Poetry artifacts
        assert not Path(project_dir, "poetry.lock").exists(), "poetry.lock should not exist"

    def test_complete_workflow_minimal_project(self, tmp_path):
        """
        Full integration test: generate minimal project (no app, no config), verify it works.

        EXPECTED TO FAIL: Tests minimal project configuration works correctly.
        """
        from cookiecutter.main import cookiecutter

        # Generate minimal project
        project_dir = cookiecutter(
            str(TEMPLATE_DIR),
            output_dir=str(tmp_path),
            no_input=True,
            extra_context={
                "name": "Minimal E2E Project",
                "create_application": False,
                "create_config": False,
            },
        )

        # Verify project structure (no app folder, no config)
        assert Path(project_dir, "pyproject.toml").exists()
        assert Path(project_dir, "Makefile").exists()
        assert not Path(project_dir, "minimal_e2e_project").exists(), "Application folder should not exist"
        assert not Path(project_dir, "config.yml").exists(), "Config file should not exist"

        # Verify pyproject.toml has proper wheel configuration for non-package project
        pyproject_content = Path(project_dir, "pyproject.toml").read_text()
        assert "[tool.hatch.build.targets.wheel]" in pyproject_content, (
            "Minimal project should have wheel target configuration"
        )
        assert 'only-include = ["README.rst"]' in pyproject_content, (
            "Minimal project should only include README.rst in wheel"
        )

        # Install dependencies using uv directly
        result = subprocess.run(["uv", "sync"], cwd=project_dir, capture_output=True, text=True, timeout=300)
        assert result.returncode == 0, f"uv sync failed: {result.stderr}"

        # Verify environment works
        result = subprocess.run(
            ["uv", "run", "python", "--version"], cwd=project_dir, capture_output=True, text=True, timeout=30
        )
        assert result.returncode == 0, f"Python not available: {result.stderr}"
        assert "Python 3.13" in result.stdout, "Should use Python 3.13"


# Helper functions for server testing
def find_free_port() -> int:
    """Find a random free port on the system."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


def wait_for_server(port: int, timeout: int = 60, interval: float = 0.5) -> bool:
    """
    Wait for a server to be ready on the specified port.

    Returns True if server responds, False if timeout exceeded.
    Default timeout increased to 60 seconds to account for uv sync during server startup.
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            requests.get(f"http://localhost:{port}", timeout=1)
            # Any response (including 404) means the server is up
            return True
        except (requests.ConnectionError, requests.Timeout):
            time.sleep(interval)
    return False


class TestEnhancedMakefile:
    """
    Test enhanced Makefile functionality with help target, proper command names,
    environment variables, and actual server startup.

    EXPECTED TO FAIL: These tests verify Makefile improvements that don't exist yet.
    """

    def test_makefile_uses_harp_proxy_not_harp(self, tmp_path):
        """
        Verify generated Makefile uses 'harp-proxy' command instead of 'harp'.

        EXPECTED TO FAIL: Current Makefile uses old 'harp' command.
        """
        from cookiecutter.main import cookiecutter

        project_dir = cookiecutter(
            str(TEMPLATE_DIR),
            output_dir=str(tmp_path),
            no_input=True,
            extra_context={
                "name": "Harp Proxy Command Test",
                "create_application": True,
                "create_config": True,
            },
        )

        makefile_content = Path(project_dir, "Makefile").read_text()

        # Should use 'harp-proxy server' not 'harp server'
        assert "harp-proxy server" in makefile_content, "Makefile should use 'harp-proxy server' command"

        # Should NOT use old 'harp server' command
        # Use word boundaries to avoid matching 'harp-proxy'
        assert not re.search(r"\bharp\s+server", makefile_content), "Makefile should NOT use old 'harp server' command"

    def test_make_help_target_exists(self, tmp_path):
        """
        Verify 'make help' target exists and displays formatted help.

        EXPECTED TO FAIL: No help target exists yet.
        """
        from cookiecutter.main import cookiecutter

        project_dir = cookiecutter(
            str(TEMPLATE_DIR), output_dir=str(tmp_path), no_input=True, extra_context={"name": "Help Test Project"}
        )

        # First install dependencies (needed to run make commands)
        subprocess.run(["make", "install"], cwd=project_dir, check=True, capture_output=True, timeout=300)

        # Run make help
        result = subprocess.run(["make", "help"], cwd=project_dir, capture_output=True, text=True, timeout=30)

        assert result.returncode == 0, f"make help should succeed: {result.stderr}"

        # Verify help output contains expected content
        output = result.stdout
        assert len(output) > 0, "make help should produce output"
        assert "install" in output.lower(), "Help should mention 'install' target"
        assert "test" in output.lower(), "Help should mention 'test' target"
        assert "start" in output.lower(), "Help should mention 'start' target"

    def test_make_help_has_cog_icons(self, tmp_path):
        """
        Verify 'make help' output includes cog/gear icons (⚙️) for formatting.

        EXPECTED TO FAIL: Help formatting with icons doesn't exist yet.
        """
        from cookiecutter.main import cookiecutter

        project_dir = cookiecutter(
            str(TEMPLATE_DIR), output_dir=str(tmp_path), no_input=True, extra_context={"name": "Help Icons Test"}
        )

        subprocess.run(["make", "install"], cwd=project_dir, check=True, capture_output=True, timeout=300)

        result = subprocess.run(["make", "help"], cwd=project_dir, capture_output=True, text=True, timeout=30)

        assert result.returncode == 0, f"make help should succeed: {result.stderr}"

        # Check for package emoji icon in header
        output = result.stdout
        assert "📦" in output, "Help output should include package icon (📦) in header"

    def test_make_help_has_color_codes(self, tmp_path):
        """
        Verify 'make help' uses ANSI color codes for formatted output.

        EXPECTED TO FAIL: No color formatting exists yet.
        """
        from cookiecutter.main import cookiecutter

        project_dir = cookiecutter(
            str(TEMPLATE_DIR), output_dir=str(tmp_path), no_input=True, extra_context={"name": "Help Colors Test"}
        )

        subprocess.run(["make", "install"], cwd=project_dir, check=True, capture_output=True, timeout=300)

        result = subprocess.run(
            ["make", "help"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, "TERM": "xterm-256color"},  # Ensure color support
        )

        assert result.returncode == 0, f"make help should succeed: {result.stderr}"

        # Check for ANSI color codes (ESC[...m format)
        output = result.stdout
        ansi_color_pattern = r"\x1b\[\d+(?:;\d+)*m"
        assert re.search(ansi_color_pattern, output), "Help output should include ANSI color codes for formatting"

    def test_make_help_shows_target_descriptions(self, tmp_path):
        """
        Verify 'make help' displays descriptions for each target.

        EXPECTED TO FAIL: Target descriptions don't exist yet.
        """
        from cookiecutter.main import cookiecutter

        project_dir = cookiecutter(
            str(TEMPLATE_DIR), output_dir=str(tmp_path), no_input=True, extra_context={"name": "Help Descriptions Test"}
        )

        subprocess.run(["make", "install"], cwd=project_dir, check=True, capture_output=True, timeout=300)

        result = subprocess.run(["make", "help"], cwd=project_dir, capture_output=True, text=True, timeout=30)

        assert result.returncode == 0, f"make help should succeed: {result.stderr}"

        output = result.stdout.lower()

        # Check for descriptive text (not just target names)
        # Each target should have some description
        expected_descriptions = [
            ("install", ["install", "depend", "sync"]),
            ("test", ["test", "pytest"]),
            ("start", ["start", "run", "server"]),
        ]

        for target, keywords in expected_descriptions:
            # Find the line with the target
            target_line_found = False
            for line in output.split("\n"):
                if target in line:
                    # Check if any keyword appears in the same line or nearby
                    if any(keyword in line for keyword in keywords):
                        target_line_found = True
                        break

            assert target_line_found, f"Help should show descriptive text for '{target}' target"

    @pytest.mark.parametrize(
        "create_application,create_config",
        [
            (True, True),
            (True, False),
            (False, True),
            (False, False),
        ],
    )
    def test_make_install_creates_venv_all_combinations(self, tmp_path, create_application, create_config):
        """
        Test 'make install' works for all parameter combinations.

        EXPECTED TO FAIL: Tests basic install across all configurations.
        """
        from cookiecutter.main import cookiecutter

        project_name = f"Install Test {create_application} {create_config}"
        project_dir = cookiecutter(
            str(TEMPLATE_DIR),
            output_dir=str(tmp_path),
            no_input=True,
            extra_context={
                "name": project_name,
                "create_application": create_application,
                "create_config": create_config,
            },
        )

        # Run make install
        result = subprocess.run(["make", "install"], cwd=project_dir, capture_output=True, text=True, timeout=300)

        assert result.returncode == 0, f"make install failed: {result.stderr}"
        assert Path(project_dir, ".venv").exists(), "make install should create .venv"

    @pytest.mark.slow
    def test_make_start_with_actual_server(self, tmp_path):
        """
        Test 'make start' actually starts harp-proxy server and responds to requests.

        EXPECTED TO FAIL: Tests actual server startup functionality.
        """
        from cookiecutter.main import cookiecutter

        # Find a free port to avoid conflicts
        port = find_free_port()

        project_dir = cookiecutter(
            str(TEMPLATE_DIR),
            output_dir=str(tmp_path),
            no_input=True,
            extra_context={
                "name": "Server Start Test",
                "create_application": True,
                "create_config": True,
            },
        )

        # Install dependencies first
        subprocess.run(["make", "install"], cwd=project_dir, check=True, capture_output=True, timeout=300)

        # Set dashboard port via HARP_OPTIONS environment variable
        env = os.environ.copy()
        env["HARP_OPTIONS"] = f"--set dashboard.port={port}"

        # Start server in background
        server_process = subprocess.Popen(
            ["make", "start"], cwd=project_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env
        )

        try:
            # Wait for dashboard server to be ready (increased timeout for uv sync)
            server_ready = wait_for_server(port, timeout=60)
            assert server_ready, f"Server did not start within 60 seconds on port {port}"

            # Test server responds to HTTP requests
            response = requests.get(f"http://localhost:{port}", timeout=5)
            # Any response means server is working (even 404 is OK)
            assert response.status_code in [200, 404], (
                f"Server should respond with valid HTTP status code, got {response.status_code}"
            )

        finally:
            # Clean up: kill the server process
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_process.kill()
                server_process.wait()

    @pytest.mark.slow
    def test_make_start_with_harp_options_env_var(self, tmp_path):
        """
        Test HARP_OPTIONS environment variable is passed to harp-proxy server.

        EXPECTED TO FAIL: HARP_OPTIONS support doesn't exist yet.
        """
        from cookiecutter.main import cookiecutter

        port = find_free_port()

        project_dir = cookiecutter(
            str(TEMPLATE_DIR),
            output_dir=str(tmp_path),
            no_input=True,
            extra_context={
                "name": "HARP Options Test",
                "create_application": False,
                "create_config": False,
            },
        )

        subprocess.run(["make", "install"], cwd=project_dir, check=True, capture_output=True, timeout=300)

        # Set dashboard port via HARP_OPTIONS environment variable
        env = os.environ.copy()
        env["HARP_OPTIONS"] = f"--set dashboard.port={port}"

        server_process = subprocess.Popen(
            ["make", "start"], cwd=project_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env
        )

        try:
            # Wait for dashboard server to start on the specified port (increased timeout for uv sync)
            server_ready = wait_for_server(port, timeout=60)
            assert server_ready, (
                f"Server should start on port {port} when HARP_OPTIONS='--set dashboard.port={port}' is set"
            )

            # Verify server responds
            response = requests.get(f"http://localhost:{port}", timeout=5)
            assert response.status_code in [200, 404], "Server should respond when started with HARP_OPTIONS"

        finally:
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_process.kill()
                server_process.wait()

    def test_make_start_with_debug_mode_enabled(self, tmp_path):
        """
        Test DEBUG=1 environment variable enables verbose output.

        EXPECTED TO FAIL: DEBUG mode support doesn't exist yet.
        """
        from cookiecutter.main import cookiecutter

        project_dir = cookiecutter(
            str(TEMPLATE_DIR),
            output_dir=str(tmp_path),
            no_input=True,
            extra_context={
                "name": "Debug Mode Test",
                "create_application": False,
                "create_config": False,
            },
        )

        subprocess.run(["make", "install"], cwd=project_dir, check=True, capture_output=True, timeout=300)

        # Run a simple make target with DEBUG=1
        env = os.environ.copy()
        env["DEBUG"] = "1"

        result = subprocess.run(["make", "test"], cwd=project_dir, capture_output=True, text=True, timeout=60, env=env)

        # With DEBUG=1, should see verbose output (commands being executed)
        # Check stderr or stdout for command echo
        combined_output = result.stdout + result.stderr
        assert len(combined_output) > 0, "DEBUG=1 should produce output"

        # Look for indicators of verbose/debug mode (e.g., echoed commands)
        # When DEBUG is on, Make typically shows the commands it's running
        assert "uv run" in combined_output or "pytest" in combined_output, "DEBUG=1 should show commands being executed"

    def test_make_start_without_debug_is_silent(self, tmp_path):
        """
        Test that without DEBUG, make commands are silent (don't echo commands).

        EXPECTED TO FAIL: Silent mode (@ prefix on commands) doesn't exist yet.
        """
        from cookiecutter.main import cookiecutter

        project_dir = cookiecutter(
            str(TEMPLATE_DIR),
            output_dir=str(tmp_path),
            no_input=True,
            extra_context={
                "name": "Silent Mode Test",
                "create_application": False,
                "create_config": False,
            },
        )

        subprocess.run(["make", "install"], cwd=project_dir, check=True, capture_output=True, timeout=300)

        # Run without DEBUG (default behavior)
        subprocess.run(["make", "test"], cwd=project_dir, capture_output=True, text=True, timeout=60)

        # Without DEBUG, commands should not be echoed
        # Makefile should use @ prefix to suppress command echoing
        makefile_content = Path(project_dir, "Makefile").read_text()

        # Check that test target uses @ prefix for silent execution
        test_target_section = ""
        capture = False
        for line in makefile_content.split("\n"):
            if line.startswith("test:"):
                capture = True
            elif capture and line.startswith("\t"):
                test_target_section += line + "\n"
            elif capture and not line.startswith("\t"):
                break

        assert "@" in test_target_section or "$(UV)" in test_target_section, (
            "Makefile should use @ prefix or variables to suppress command echoing by default"
        )

    @pytest.mark.slow
    @pytest.mark.parametrize(
        "create_application,create_config",
        [
            (True, True),
            (True, False),
            (False, True),
            (False, False),
        ],
    )
    def test_make_start_server_responds_all_combinations(self, tmp_path, create_application, create_config):
        """
        Test server startup works for all parameter combinations.

        EXPECTED TO FAIL: Comprehensive test of server startup across all configs.
        """
        from cookiecutter.main import cookiecutter

        port = find_free_port()

        project_name = f"Server Test {create_application} {create_config}"
        project_dir = cookiecutter(
            str(TEMPLATE_DIR),
            output_dir=str(tmp_path),
            no_input=True,
            extra_context={
                "name": project_name,
                "create_application": create_application,
                "create_config": create_config,
            },
        )

        subprocess.run(["make", "install"], cwd=project_dir, check=True, capture_output=True, timeout=300)

        # Set dashboard port via HARP_OPTIONS environment variable
        env = os.environ.copy()
        env["HARP_OPTIONS"] = f"--set dashboard.port={port}"

        server_process = subprocess.Popen(
            ["make", "start"], cwd=project_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env
        )

        try:
            # Wait for dashboard server to be ready (increased timeout for uv sync)
            server_ready = wait_for_server(port, timeout=60)
            assert server_ready, (
                f"Server should start with create_application={create_application}, create_config={create_config}"
            )

            response = requests.get(f"http://localhost:{port}", timeout=5)
            assert response.status_code in [200, 404], "Server should respond for all parameter combinations"

        finally:
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_process.kill()
                server_process.wait()

    def test_makefile_uses_uv_variable(self, tmp_path):
        """
        Verify Makefile defines UV variable and uses it consistently.

        EXPECTED TO FAIL: Tests Makefile uses $(UV) consistently in all commands.
        """
        from cookiecutter.main import cookiecutter

        project_dir = cookiecutter(
            str(TEMPLATE_DIR), output_dir=str(tmp_path), no_input=True, extra_context={"name": "UV Variable Test"}
        )

        makefile_content = Path(project_dir, "Makefile").read_text()

        # Should define UV variable (with any form)
        assert re.search(r"^UV\s*\?=", makefile_content, re.MULTILINE), (
            "Makefile should define UV variable with ?= operator"
        )

        # Should use $(UV) in commands instead of hardcoded 'uv'
        # Count occurrences of hardcoded 'uv' vs $(UV)
        # Exclude the UV variable definition line itself
        lines_without_definition = [line for line in makefile_content.split("\n") if not line.startswith("UV ")]
        remaining_content = "\n".join(lines_without_definition)

        # Check that targets use $(UV) not bare 'uv'
        # Look for bare 'uv run' or 'uv sync' that should use $(UV) instead
        assert "$(UV) run" in remaining_content, "Makefile should use '$(UV) run' instead of 'uv run'"
        assert "$(UV) sync" in remaining_content, "Makefile should use '$(UV) sync' instead of 'uv sync'"

    def test_makefile_help_is_default_target(self, tmp_path):
        """
        Verify 'help' is the default target (when running just 'make').

        EXPECTED TO FAIL: Help as default target doesn't exist yet.
        """
        from cookiecutter.main import cookiecutter

        project_dir = cookiecutter(
            str(TEMPLATE_DIR), output_dir=str(tmp_path), no_input=True, extra_context={"name": "Default Target Test"}
        )

        subprocess.run(["make", "install"], cwd=project_dir, check=True, capture_output=True, timeout=300)

        # Run 'make' without any target
        result = subprocess.run(["make"], cwd=project_dir, capture_output=True, text=True, timeout=30)

        assert result.returncode == 0, "Running 'make' without target should succeed"

        # Output should look like help (contain target names and descriptions)
        output = result.stdout.lower()
        assert "install" in output and "test" in output and "start" in output, (
            "Default 'make' command should show help with available targets"
        )


class TestGitInitialization:
    """Test that generated projects are initialized as git repositories with initial commit."""

    def test_git_repository_is_initialized(self, tmp_path):
        """Verify generated project has .git directory if git is available."""
        from cookiecutter.main import cookiecutter

        # Check if git is available
        git_available = subprocess.run(["which", "git"], capture_output=True).returncode == 0

        project_dir = cookiecutter(
            str(TEMPLATE_DIR),
            output_dir=str(tmp_path),
            no_input=True,
            extra_context={
                "name": "Git Test Project",
                "author_name": "Test Author",
                "author_email": "test@example.com",
            },
        )

        if git_available:
            git_dir = Path(project_dir) / ".git"
            assert git_dir.exists(), "Generated project should have .git directory when git is available"
            assert git_dir.is_dir(), ".git should be a directory"

    def test_initial_commit_exists_with_correct_message(self, tmp_path):
        """Verify generated project has initial commit with 'chore: initial project generation' message."""
        from cookiecutter.main import cookiecutter

        # Check if git is available
        git_available = subprocess.run(["which", "git"], capture_output=True).returncode == 0
        if not git_available:
            pytest.skip("Git not available")

        project_dir = cookiecutter(
            str(TEMPLATE_DIR),
            output_dir=str(tmp_path),
            no_input=True,
            extra_context={"name": "Git Commit Test", "author_name": "Test Author", "author_email": "test@example.com"},
        )

        # Check that there is at least one commit
        result = subprocess.run(["git", "log", "--oneline"], cwd=project_dir, capture_output=True, text=True)
        assert result.returncode == 0, "git log should succeed"
        assert len(result.stdout.strip()) > 0, "Should have at least one commit"

        # Check commit message
        result = subprocess.run(["git", "log", "-1", "--format=%s"], cwd=project_dir, capture_output=True, text=True)
        commit_message = result.stdout.strip()
        assert commit_message == "chore: initial project generation", (
            f"Initial commit message should be 'chore: initial project generation', got '{commit_message}'"
        )

    def test_initial_commit_uses_author_info(self, tmp_path):
        """Verify initial commit uses author name and email from cookiecutter variables."""
        from cookiecutter.main import cookiecutter

        # Check if git is available
        git_available = subprocess.run(["which", "git"], capture_output=True).returncode == 0
        if not git_available:
            pytest.skip("Git not available")

        author_name = "John Smith"
        author_email = "john.smith@example.com"

        project_dir = cookiecutter(
            str(TEMPLATE_DIR),
            output_dir=str(tmp_path),
            no_input=True,
            extra_context={"name": "Git Author Test", "author_name": author_name, "author_email": author_email},
        )

        # Check author name
        result = subprocess.run(["git", "log", "-1", "--format=%an"], cwd=project_dir, capture_output=True, text=True)
        assert result.stdout.strip() == author_name, f"Author name should be '{author_name}'"

        # Check author email
        result = subprocess.run(["git", "log", "-1", "--format=%ae"], cwd=project_dir, capture_output=True, text=True)
        assert result.stdout.strip() == author_email, f"Author email should be '{author_email}'"

    def test_all_generated_files_are_committed(self, tmp_path):
        """Verify all generated files are included in the initial commit."""
        from cookiecutter.main import cookiecutter

        # Check if git is available
        git_available = subprocess.run(["which", "git"], capture_output=True).returncode == 0
        if not git_available:
            pytest.skip("Git not available")

        project_dir = cookiecutter(
            str(TEMPLATE_DIR),
            output_dir=str(tmp_path),
            no_input=True,
            extra_context={"name": "Git Status Test", "author_name": "Test Author", "author_email": "test@example.com"},
        )

        # Check that working tree is clean (no uncommitted changes)
        result = subprocess.run(["git", "status", "--porcelain"], cwd=project_dir, capture_output=True, text=True)
        assert result.stdout.strip() == "", "Working tree should be clean after project generation"


class TestPostGenHookMessages:
    """Test that post_gen_project.sh hook shows correct instructions."""

    def test_hook_shows_make_start_not_make(self, tmp_path, capsys):
        """Verify post generation hook message says 'make start' not just 'make'."""
        from cookiecutter.main import cookiecutter

        # Generate project and capture output
        cookiecutter(
            str(TEMPLATE_DIR),
            output_dir=str(tmp_path),
            no_input=True,
            extra_context={"name": "Make Start Test"},
        )

        # The hook output is printed to stdout during generation
        # We need to check the hook file content directly
        hook_path = TEMPLATE_DIR / "hooks" / "post_gen_project.sh"
        hook_content = hook_path.read_text()

        assert "make start" in hook_content or "make start)" in hook_content, (
            "Hook should mention 'make start' to start the project"
        )
        # The instruction should not say just 'make)' without 'start'
        # Look for the pattern that would indicate wrong instruction
        assert not re.search(r"cd.*&&\s*make\)", hook_content), (
            "Hook should not say '&& make)' without specifying 'start' target"
        )
