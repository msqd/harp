"""Generate a commented, source-introspected example ``config.yml``.

The example lists every setting of every default application with its default value, fully
commented out, so a freshly scaffolded project ships a self-documenting configuration reference
that stays in sync with the actual Pydantic settings models.
"""

import yaml

from harp.config.asdict import asdict
from harp.config.builders.configuration import ConfigurationBuilder

DOCS_BASE_URL = "https://docs.harp-proxy.net/en/latest"

_HEADER = (
    "# =============================================================================\n"
    "# HARP Proxy configuration\n"
    "# =============================================================================\n"
    "# Every available setting is listed below with its default value, commented out.\n"
    "# Uncomment a section and edit the values you want to override.\n"
    "# Documentation: https://docs.harp-proxy.net/\n"
    "# ============================================================================="
)


def iter_app_settings(builder: ConfigurationBuilder | None = None):
    """Yield ``(app_name, default_settings)`` for each default application that defines settings.

    ``app_name`` is the top-level configuration key (the application's short name); applications
    without a settings model (e.g. ``janitor``) are skipped.
    """
    builder = builder or ConfigurationBuilder()
    for name, app in builder.applications.items():
        settings_type = app.settings_type
        if settings_type is dict:
            continue
        yield name, asdict(settings_type(), verbose=True)


def _comment(text: str) -> str:
    return "\n".join(f"# {line}" if line else "#" for line in text.splitlines())


def _render_section(name: str, settings: dict) -> str:
    title = name.replace("_", " ").title()
    body = yaml.safe_dump({name: settings}, sort_keys=False, default_flow_style=False).rstrip("\n")
    return (
        "# -----------------------------------------------------------------------------\n"
        f"# {title}\n"
        f"# See: {DOCS_BASE_URL}/apps/{name}/\n"
        "# -----------------------------------------------------------------------------\n"
        f"{_comment(body)}"
    )


def render_example_config(builder: ConfigurationBuilder | None = None) -> str:
    """Render a fully-commented reference ``config.yml`` for all default applications."""
    sections = [_HEADER]
    for name, settings in iter_app_settings(builder):
        sections.append(_render_section(name, settings))
    return "\n\n".join(sections) + "\n"
