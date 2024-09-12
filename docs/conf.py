# Configuration file for the Sphinx documentation builder.

import builtins
import os
import sys
from datetime import datetime

builtins.__sphinx__ = True

sys.path.insert(0, os.path.abspath(".."))

project = "HARP Proxy"

first_year, current_year = 2023, datetime.now().year
author = "Romain Dorgueil"
copyright = f"{current_year}, {author}"
if current_year > first_year:
    copyright = str(first_year) + "-" + copyright


READTHEDOCS_VERSION = os.environ.get("READTHEDOCS_VERSION")

if os.environ.get("READTHEDOCS_GIT_IDENTIFIER"):
    version = release = os.environ["READTHEDOCS_GIT_IDENTIFIER"]
else:
    version = release = ".".join(__import__("harp").__hardcoded_version__.split(".")[0:2])

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.coverage",
    "sphinx.ext.graphviz",
    "sphinx.ext.ifconfig",
    "sphinx.ext.inheritance_diagram",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinx.ext.viewcode",
    "sphinx_click",
    "sphinx_copybutton",
    "sphinx_design",
    "sphinx_sitemap",
    "sphinx_tags",
    "sphinxcontrib.jquery",
    "docs._extensions.jsonschema",
    "docs._extensions.services",
]

ALGOLIA_APIKEY = os.getenv("ALGOLIA_APIKEY")
if ALGOLIA_APIKEY and READTHEDOCS_VERSION == "latest":
    extensions.append("sphinx_docsearch")

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

root_doc = "index"

html_title = project + " " + version
html_theme = "furo"
html_static_path = ["_static"]
html_theme_options = {
    "light_logo": "logo.png",
    "dark_logo": "logo.png",
}
html_favicon = "favicon.ico"
html_js_files = ["js/links-target-blank.js"]
html_css_files = ["css/harp.css"]

html_baseurl = os.getenv("READTHEDOCS_CANONICAL_URL", "/")

html_sidebars = {
    "**": [
        "sidebar/analytics.html",
        "sidebar/scroll-start.html",
        "sidebar/brand.html",
        "sidebar/search.html",
        "sidebar/navigation.html",
        "sidebar/scroll-end.html",
    ]
}

todo_include_todos = True
html_show_sphinx = False

tags_create_tags = True
tags_create_badges = True
tags_badge_colors = {"events": "primary"}
tags_page_title = "With tags"

autodoc_typehints = "description"
autodoc_member_order = "groupwise"
autodoc_default_flags = ["members", "undoc-members", "show-inheritance"]
autodoc_class_signature = "separated"

autoclass_content = "both"
add_module_names = False
pygments_style = "sphinx"
graphviz_output_format = "svg"

inheritance_graph_attrs = {
    "rankdir": "TB",
    "size": '"8.0, 12.0"',
    "fontsize": 14,
    "ratio": "compress",
}

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "structlog": ("https://www.structlog.org/en/stable", None),
    "whistle": ("https://python-whistle.readthedocs.io/latest", None),
    "redis": ("https://redis-py.readthedocs.io/en/stable", None),
}

if ALGOLIA_APIKEY and READTHEDOCS_VERSION == "latest":
    docsearch_app_id = "ZPR2CBYLG3"
    docsearch_api_key = ALGOLIA_APIKEY
    docsearch_index_name = "harp-proxy"

if READTHEDOCS_VERSION and READTHEDOCS_VERSION != "latest":
    rst_prolog = (
        """
    .. admonition::

        This documentation is for an **unreleased** version of HARP Proxy.
        For the latest released version, see `latest <https://docs.harp-proxy.net/en/latest>`_.

    """.strip()
        + "\n\n"
    )
