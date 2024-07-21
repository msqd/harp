# Configuration file for the Sphinx documentation builder.

import builtins
import os
import sys
from datetime import datetime

builtins.__sphinx__ = True

sys.path.insert(0, os.path.abspath(".."))

project = "Harp Proxy"

import pprint

pprint.pprint(os.environ)

first_year, current_year = 2023, datetime.now().year
author = "Romain Dorgueil"
copyright = f"{current_year}, {author}"
if current_year > first_year:
    copyright = str(first_year) + "-" + copyright
version = release = ".".join(__import__("harp").__version__.split(".")[0:2])

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.coverage",
    "sphinx.ext.graphviz",
    "sphinx.ext.ifconfig",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinx.ext.viewcode",
    "sphinx_copybutton",
    "sphinx_design",
    "sphinx_sitemap",
    "sphinxcontrib.jquery",
    "sphinx_click",
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

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "structlog": ("https://www.structlog.org/en/stable", None),
    "whistle": ("https://python-whistle.readthedocs.io/latest", None),
}

rst_prolog = """.. attention::
    This is the documentation for `HARP Proxy <https://harp-proxy.net/>`_, actually published as an **early preview**.
    Both the software and documentation are a work in progress, and although we already use it on various production
    servers, they may contain inaccuracies, typographical errors, huge mistakes and empty pages. We work hard to
    eradicate all mistakes and implement stuff, but it is a long and tedious process. We appreciate your patience and
    understanding. Of course, any :doc:`help will be greatly appreciated </contribute/index>`.
"""
