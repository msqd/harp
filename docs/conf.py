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
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinx.ext.viewcode",
    "sphinx.ext.inheritance_diagram",
    "sphinx_copybutton",
    "sphinx_design",
    "sphinx_sitemap",
    "sphinxcontrib.jquery",
    "sphinx_click",
    "docs._extensions.services",
]

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
html_baseurl = "https://docs.harp-proxy.net/en/latest/"

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

autodoc_typehints = "description"
autodoc_member_order = "groupwise"
autodoc_default_flags = ["members", "undoc-members", "show-inheritance"]
autodoc_class_signature = "separated"

autoclass_content = "both"
add_module_names = False
pygments_style = "sphinx"
graphviz_output_format = "svg"

inheritance_graph_attrs = {"rankdir": "TB", "size": '"8.0, 12.0"', "fontsize": 14, "ratio": "compress"}

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "structlog": ("https://www.structlog.org/en/stable", None),
    "whistle": ("https://python-whistle.readthedocs.io/latest", None),
    "redis": ("https://redis-py.readthedocs.io/en/stable", None),
}

rst_prolog = (
    """
.. admonition:: HARP Proxy is currently an Early Preview

   Please apologize for mistakes, typos, etc. We put great effort into writing good docs, but we are humans... If you
   spot anything strange, :doc:`help will be greatly appreciated </contribute/index>`.

""".strip()
    + "\n\n"
)
if version == "0.7":
    rst_prolog = (
        """
.. attention::

    **THIS IS THE DOCUMENTATION FOR THE 0.7 VERSION OF HARP PROXY. IT IS A FUTURE RELEASE AND THE DOCUMENTATION IS
    NOT IN SYNC WITH THE CODEBASE, AS IT CONTAINS NOT-YET-MERGED FEATURES. PLEASE REFER TO THE LATEST RELEASE INSTEAD.**

""".strip()
        + "\n\n"
    )
