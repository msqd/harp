"""
Tests for cookiecutter template content to verify uv migration.

These tests verify that the cookiecutter template at harp/commandline/cookiecutters/project/
has been properly migrated from Poetry to uv.

IMPORTANT: These tests are expected to FAIL initially because the template files
still use Poetry. They will pass once the migration is complete.
"""

import re
from pathlib import Path

import pytest


# Path to the cookiecutter template directory
TEMPLATE_DIR = Path(__file__).parent.parent / "harp" / "commandline" / "cookiecutters" / "project"
TEMPLATE_PROJECT_DIR = TEMPLATE_DIR / "{{cookiecutter.__dir_name}}"


class TestPyprojectToml:
    """Test pyproject.toml template uses PEP 621 and hatchling, not Poetry."""

    @pytest.fixture
    def pyproject_content(self):
        """Read the pyproject.toml template file."""
        pyproject_path = TEMPLATE_PROJECT_DIR / "pyproject.toml"
        return pyproject_path.read_text()

    def test_uses_pep621_project_section(self, pyproject_content):
        """Verify pyproject.toml uses [project] section instead of [tool.poetry]."""
        assert "[project]" in pyproject_content, "pyproject.toml should use PEP 621 [project] section"
        assert "[tool.poetry]" not in pyproject_content, "pyproject.toml should not contain [tool.poetry] section"

    def test_uses_hatchling_build_system(self, pyproject_content):
        """Verify build-system uses hatchling instead of poetry-core."""
        assert "hatchling.build" in pyproject_content, "build-backend should use hatchling"
        assert "poetry-core" not in pyproject_content, "should not use poetry-core build backend"
        assert 'requires = ["hatchling"]' in pyproject_content, "build-system requires should specify hatchling"

    def test_python_version_is_3_13(self, pyproject_content):
        """Verify Python version is >=3.13,<3.14."""
        assert 'requires-python = ">=3.13,<3.14"' in pyproject_content, "Python version should be >=3.13,<3.14"
        assert "^3.12" not in pyproject_content, "should not use Poetry's ^3.12 syntax"

    def test_has_harp_proxy_dependency(self, pyproject_content):
        """Verify harp-proxy dependency exists in dependencies list."""
        # In PEP 621, dependencies are in [project] section
        assert "dependencies" in pyproject_content, "should have dependencies key"
        assert "harp-proxy" in pyproject_content, "should depend on harp-proxy"

    def test_harp_proxy_is_pinned_to_at_least_0_10(self, pyproject_content):
        """Verify harp-proxy is pinned to >=0.10.0.

        The generated config.yml is a fully-commented reference that only loads without crashing
        from harp-proxy 0.10.0 onwards (the empty/comments-only config loader fix). An unpinned
        dependency would let a scaffold install an older release and crash on ``make start``.
        """
        assert "harp-proxy>=0.10.0" in pyproject_content, "harp-proxy should be pinned to >=0.10.0"

    def test_package_mode_conditional_preserved(self, pyproject_content):
        """Verify hatchling build configuration conditional logic is preserved for Jinja2."""
        # The conditional logic should use hatchling build config for non-package projects
        assert "[tool.hatch.build.targets.wheel]" in pyproject_content, (
            "hatchling build config should be present for non-package projects"
        )
        assert "{%- if not cookiecutter.create_application" in pyproject_content, (
            "Jinja2 conditional for non-package projects should be preserved"
        )
        assert 'only-include = ["README.rst"]' in pyproject_content, (
            "Non-package projects should only include README.rst"
        )

    def test_has_project_metadata_fields(self, pyproject_content):
        """Verify project metadata fields use PEP 621 format."""
        assert 'name = "{{cookiecutter.__pkg_name}}"' in pyproject_content
        assert 'version = "0.1.0"' in pyproject_content
        assert "description =" in pyproject_content
        assert "authors =" in pyproject_content
        assert 'readme = "README.rst"' in pyproject_content or 'readme = { file = "README.rst"' in pyproject_content

    def test_authors_format_is_pep621_compatible(self, pyproject_content):
        """Verify authors field uses PEP 621 format (list of dicts with name and email)."""
        # PEP 621 format: authors = [{name = "...", email = "..."}]
        # Not Poetry format: authors = ["Name <email>"]
        if "authors = [" in pyproject_content:
            # Check it's not the Poetry string format
            assert not re.search(r'authors\s*=\s*\[\s*"[^"]+\s*<[^>]+>"', pyproject_content), (
                "authors should not use Poetry's string format"
            )


class TestMakefile:
    """Test Makefile template uses uv commands, not poetry."""

    @pytest.fixture
    def makefile_content(self):
        """Read the Makefile template file."""
        makefile_path = TEMPLATE_PROJECT_DIR / "Makefile"
        return makefile_path.read_text()

    def test_defines_uv_variable(self, makefile_content):
        """Verify Makefile defines UV variable instead of POETRY."""
        assert "UV ?=" in makefile_content, "Makefile should define UV variable"
        assert "POETRY ?=" not in makefile_content, "Makefile should not define POETRY variable"

    def test_install_target_uses_uv_sync(self, makefile_content):
        """Verify install target uses 'uv sync' command."""
        # Should have sync command (either literal or via variable)
        assert "sync" in makefile_content, "install target should use sync command"
        assert "uv sync" in makefile_content or "$(UV) sync" in makefile_content, (
            "install target should use 'uv sync' or '$(UV) sync'"
        )
        assert "poetry install" not in makefile_content, "should not use 'poetry install'"

    def test_start_target_uses_uv_run(self, makefile_content):
        """Verify start target uses 'uv run harp-proxy server'."""
        # Should have harp-proxy server command
        assert "harp-proxy server" in makefile_content, "start target should use 'harp-proxy server'"
        assert "uv run" in makefile_content or "$(UV) run" in makefile_content, (
            "start target should use 'uv run' or '$(UV) run'"
        )
        assert "poetry run" not in makefile_content, "should not use 'poetry run'"

    def test_test_target_uses_uv_run_pytest(self, makefile_content):
        """Verify test target uses 'uv run pytest'."""
        # Should have pytest command (either literal or via variable)
        assert "pytest" in makefile_content, "test target should run pytest"
        assert "uv run pytest" in makefile_content or "$(UV) run pytest" in makefile_content, (
            "test target should use 'uv run pytest' or '$(UV) run pytest'"
        )

    def test_no_poetry_references(self, makefile_content):
        """Verify no poetry references exist in Makefile."""
        # Case-insensitive check for poetry
        assert "poetry" not in makefile_content.lower(), "Makefile should not contain any poetry references"

    def test_preserves_cookiecutter_conditionals(self, makefile_content):
        """Verify Jinja2 conditionals for create_application and create_config are preserved."""
        assert (
            "{{cookiecutter.__pkg_name}}" in makefile_content
            or "cookiecutter.create_application" in makefile_content
            or "cookiecutter.create_config" in makefile_content
        ), "Cookiecutter template variables should be preserved"


class TestPostGenProjectHook:
    """Test post_gen_project.sh hook script messages reference uv."""

    @pytest.fixture
    def hook_content(self):
        """Read the post_gen_project.sh hook file."""
        hook_path = TEMPLATE_DIR / "hooks" / "post_gen_project.sh"
        return hook_path.read_text()

    def test_success_message_mentions_make_install(self, hook_content):
        """Verify success message still mentions 'make install' (which now uses uv)."""
        # The message should still reference make commands, which internally use uv
        assert "make install" in hook_content, "should mention 'make install' command"

    def test_preserves_conditional_logic(self, hook_content):
        """Verify conditional logic for create_application and create_config is preserved."""
        assert "{{cookiecutter.create_application}}" in hook_content, "should preserve create_application conditional"
        assert "{{cookiecutter.create_config}}" in hook_content, "should preserve create_config conditional"
        assert "rm -rf ./{{cookiecutter.__pkg_name}}" in hook_content, "should preserve package cleanup logic"
        assert "rm -f ./config.yml" in hook_content, "should preserve config cleanup logic"

    def test_script_has_proper_shebang(self, hook_content):
        """Verify script starts with proper bash shebang."""
        assert hook_content.startswith("#!"), "should have shebang"
        assert "bash" in hook_content.split("\n")[0], "should use bash"


class TestReadme:
    """Test README.rst template has appropriate usage examples."""

    @pytest.fixture
    def readme_content(self):
        """Read the README.rst template file."""
        readme_path = TEMPLATE_PROJECT_DIR / "README.rst"
        return readme_path.read_text()

    def test_example_shows_make_usage(self, readme_content):
        """Verify README example shows make command (which internally uses uv)."""
        # The README should show simple make commands, not poetry-specific ones
        assert "make" in readme_content, "README should mention 'make' command"

    def test_no_poetry_references(self, readme_content):
        """Verify README does not reference poetry commands."""
        assert "poetry" not in readme_content.lower(), "README should not mention poetry"

    def test_preserves_cookiecutter_variables(self, readme_content):
        """Verify cookiecutter template variables are preserved."""
        assert "{{cookiecutter.name}}" in readme_content, "should use cookiecutter.name variable"


class TestTemplateStructure:
    """Test overall template structure and file existence."""

    def test_pyproject_toml_exists(self):
        """Verify pyproject.toml template file exists."""
        assert (TEMPLATE_PROJECT_DIR / "pyproject.toml").exists(), "pyproject.toml template should exist"

    def test_makefile_exists(self):
        """Verify Makefile template file exists."""
        assert (TEMPLATE_PROJECT_DIR / "Makefile").exists(), "Makefile template should exist"

    def test_readme_exists(self):
        """Verify README.rst template file exists."""
        assert (TEMPLATE_PROJECT_DIR / "README.rst").exists(), "README.rst template should exist"

    def test_post_gen_hook_exists(self):
        """Verify post_gen_project.sh hook exists."""
        assert (TEMPLATE_DIR / "hooks" / "post_gen_project.sh").exists(), "post_gen_project.sh hook should exist"

    def test_post_gen_hook_is_executable(self):
        """Verify post_gen_project.sh hook has executable permissions."""
        hook_path = TEMPLATE_DIR / "hooks" / "post_gen_project.sh"
        import os

        assert os.access(hook_path, os.X_OK), "post_gen_project.sh should be executable"


class TestPyprojectTomlDependencyFormat:
    """Test that dependencies use PEP 621 array format, not Poetry's table format."""

    @pytest.fixture
    def pyproject_content(self):
        """Read the pyproject.toml template file."""
        pyproject_path = TEMPLATE_PROJECT_DIR / "pyproject.toml"
        return pyproject_path.read_text()

    def test_dependencies_is_array_not_table(self, pyproject_content):
        """Verify dependencies is an array: dependencies = [...], not a table."""
        # PEP 621 format: dependencies = ["package>=1.0"]
        # Poetry format: [tool.poetry.dependencies] followed by package = "version"

        # Should have dependencies as a list
        assert re.search(r"dependencies\s*=\s*\[", pyproject_content), (
            "dependencies should be an array in PEP 621 format"
        )

        # Should not have [tool.poetry.dependencies] section
        assert "[tool.poetry.dependencies]" not in pyproject_content, (
            "should not use Poetry's dependencies table format"
        )

    def test_harp_proxy_in_dependencies_array(self, pyproject_content):
        """Verify harp-proxy is specified in dependencies array."""
        # The dependency should be in array format, could be:
        # dependencies = ["harp-proxy"]
        # or dependencies = ["harp-proxy>=0.9.0"]
        assert re.search(r'dependencies\s*=\s*\[[^\]]*"harp-proxy[^"]*"', pyproject_content), (
            "harp-proxy should be in dependencies array"
        )

    def test_has_pytest_configuration(self, pyproject_content):
        """Verify pyproject.toml has pytest configuration to prevent parent directory search."""
        # Generated projects need pytest configured to not search parent directories
        # This prevents pytest from finding the template's conftest.py
        assert "[tool.pytest.ini_options]" in pyproject_content, (
            "pyproject.toml should have [tool.pytest.ini_options] section"
        )
        # The testpaths should be set to restrict pytest to the tests directory
        assert re.search(r'testpaths\s*=\s*\[.*"tests".*\]', pyproject_content), (
            "pytest testpaths should include 'tests' directory to prevent searching parent directories"
        )


class TestMakefileVariableUsage:
    """Test that Makefile uses UV variable consistently."""

    @pytest.fixture
    def makefile_content(self):
        """Read the Makefile template file."""
        makefile_path = TEMPLATE_PROJECT_DIR / "Makefile"
        return makefile_path.read_text()

    def test_uv_variable_uses_fallback(self, makefile_content):
        """Verify UV variable has proper fallback: UV ?= $(shell which uv || echo uv)."""
        # Should define UV variable with fallback
        assert re.search(r"UV\s*\?=.*uv", makefile_content), "UV variable should be defined with uv fallback"

    def test_commands_use_uv_variable(self, makefile_content):
        """Verify commands use $(UV) variable reference."""
        # Commands should use $(UV) for consistency
        lines = makefile_content.split("\n")
        command_lines = [line for line in lines if line.startswith("\t") and "uv" in line.lower()]

        # At least some commands should use $(UV) variable
        # (Direct 'uv' usage is also acceptable, but $(UV) is more maintainable)
        assert len(command_lines) > 0, "should have commands that use uv"


class TestCookiecutterPrompts:
    """Test cookiecutter.json has helpful prompt descriptions."""

    @pytest.fixture
    def cookiecutter_json(self):
        """Read the cookiecutter.json file."""
        import json

        cookiecutter_json_path = TEMPLATE_DIR / "cookiecutter.json"
        return json.loads(cookiecutter_json_path.read_text())

    def test_has_prompts_section(self, cookiecutter_json):
        """Verify cookiecutter.json has __prompts__ section."""
        assert "__prompts__" in cookiecutter_json, "cookiecutter.json should have __prompts__ section"

    def test_name_prompt_is_descriptive(self, cookiecutter_json):
        """Verify 'name' prompt has helpful description."""
        prompts = cookiecutter_json["__prompts__"]
        assert "name" in prompts, "Should have prompt for 'name'"

        name_prompt = prompts["name"]
        # Should explain what the name is used for
        assert len(name_prompt) > 20, "Name prompt should be descriptive (>20 chars)"
        assert any(word in name_prompt.lower() for word in ["directory", "package", "generate"]), (
            "Name prompt should explain it's used to generate directory and package names"
        )

    def test_author_name_prompt_is_descriptive(self, cookiecutter_json):
        """Verify 'author_name' prompt has helpful description."""
        prompts = cookiecutter_json["__prompts__"]
        assert "author_name" in prompts, "Should have prompt for 'author_name'"

        author_name_prompt = prompts["author_name"]
        assert len(author_name_prompt) > 15, "Author name prompt should be descriptive"

    def test_author_email_prompt_is_descriptive(self, cookiecutter_json):
        """Verify 'author_email' prompt has helpful description."""
        prompts = cookiecutter_json["__prompts__"]
        assert "author_email" in prompts, "Should have prompt for 'author_email'"

        author_email_prompt = prompts["author_email"]
        assert len(author_email_prompt) > 15, "Author email prompt should be descriptive"

    def test_create_application_prompt_explains_effect(self, cookiecutter_json):
        """Verify 'create_application' prompt explains what it does."""
        prompts = cookiecutter_json["__prompts__"]
        assert "create_application" in prompts, "Should have prompt for 'create_application'"

        create_app_prompt = prompts["create_application"]
        # Should explain that it creates a folder for custom code
        assert len(create_app_prompt) > 30, "Create application prompt should explain the effect"
        assert any(word in create_app_prompt.lower() for word in ["custom", "code", "config-only"]), (
            "Create application prompt should explain it's for custom code or config-only projects"
        )

    def test_create_config_prompt_explains_effect(self, cookiecutter_json):
        """Verify 'create_config' prompt explains what it does."""
        prompts = cookiecutter_json["__prompts__"]
        assert "create_config" in prompts, "Should have prompt for 'create_config'"

        create_config_prompt = prompts["create_config"]
        # Should explain what the config file is for
        assert len(create_config_prompt) > 30, "Create config prompt should explain the effect"
        assert any(word in create_config_prompt.lower() for word in ["config", "customize", "empty"]), (
            "Create config prompt should explain it creates an empty configuration file"
        )

    def test_application_and_config_are_created_by_default(self, cookiecutter_json):
        """Verify the template defaults create both the application folder and the config file."""
        assert cookiecutter_json["create_application"] is True, "create_application should default to true"
        assert cookiecutter_json["create_config"] is True, "create_config should default to true"

    def test_all_user_facing_variables_have_prompts(self, cookiecutter_json):
        """Verify all non-internal variables have custom prompts."""
        prompts = cookiecutter_json["__prompts__"]

        # Find all variables that are user-facing (not starting with __)
        user_variables = [key for key in cookiecutter_json.keys() if not key.startswith("_")]

        for var in user_variables:
            assert var in prompts, f"User-facing variable '{var}' should have a custom prompt"


def _dev_recipe(makefile_content):
    """Return the recipe lines of the Makefile 'dev' target (empty string if absent)."""
    lines = makefile_content.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("dev:"):
            recipe = []
            for following in lines[i + 1 :]:
                if following.startswith("\t"):
                    recipe.append(following)
                elif following.strip() == "":
                    continue
                else:
                    break
            return "\n".join(recipe)
    return ""


class TestMakefileDevTarget:
    """Test the 'dev' target provides auto-reload via watchfiles."""

    @pytest.fixture
    def makefile_content(self):
        return (TEMPLATE_PROJECT_DIR / "Makefile").read_text()

    def test_dev_target_exists_and_installs_first(self, makefile_content):
        """A 'dev' target exists and depends on install (deps available before running)."""
        assert re.search(r"(?m)^dev:\s.*install", makefile_content), (
            "Makefile should define a 'dev' target depending on install"
        )

    def test_dev_target_is_phony(self, makefile_content):
        """'dev' is declared as a phony target."""
        phony_lines = [line for line in makefile_content.splitlines() if line.startswith(".PHONY")]
        assert any("dev" in line.split() for line in phony_lines), "'dev' should be listed in .PHONY"

    def test_dev_target_runs_server_with_watchfiles(self, makefile_content):
        """The dev recipe runs the harp-proxy server through watchfiles for auto-reload."""
        recipe = _dev_recipe(makefile_content)
        assert "watchfiles" in recipe, "dev target should use watchfiles"
        assert "harp-proxy server" in recipe, "dev target should run the harp-proxy server"

    def test_dev_target_watches_app_and_config_conditionally(self, makefile_content):
        """The dev recipe watches the app package and/or config.yml, guarded by the create flags."""
        recipe = _dev_recipe(makefile_content)
        assert "{% if cookiecutter.create_application %}" in recipe and "{{cookiecutter.__pkg_name}}/" in recipe, (
            "dev target should watch the application package when it is created"
        )
        assert "{% if cookiecutter.create_config %}" in recipe and "config.yml" in recipe, (
            "dev target should watch config.yml when it is created"
        )

    def test_dev_target_runs_server_directly_without_nested_uv_run(self, makefile_content):
        """watchfiles must supervise the server process itself so the port is freed before reload.

        A nested ``uv run`` wrapper absorbs watchfiles' restart signal and leaves the old server
        bound, so the reload fails with "address already in use" (observed on macOS). The outer
        ``uv run watchfiles`` already provides the environment.
        """
        recipe = _dev_recipe(makefile_content)
        assert 'watchfiles "harp-proxy server' in recipe, (
            "watchfiles should run 'harp-proxy server' directly as its child process"
        )
        assert "run harp-proxy" not in recipe, (
            "the watched command must not nest another 'uv run' (it would absorb the reload signal)"
        )


class TestPyprojectWatchfilesDependency:
    """Test watchfiles is declared so 'make dev' resolves it after 'uv sync'."""

    @pytest.fixture
    def pyproject_content(self):
        return (TEMPLATE_PROJECT_DIR / "pyproject.toml").read_text()

    def test_watchfiles_declared_as_dev_dependency(self, pyproject_content):
        """watchfiles is declared in the dev dependency group uv installs by default (not a plain extra).

        Parsed as text: the template embeds Jinja conditionals that are not valid TOML.
        """
        assert "[dependency-groups]" in pyproject_content, "should declare a [dependency-groups] table"
        assert re.search(r"(?s)\[dependency-groups\].*?dev\s*=\s*\[[^\]]*watchfiles", pyproject_content), (
            "watchfiles should be listed in the [dependency-groups] dev group so 'uv sync' installs it"
        )
