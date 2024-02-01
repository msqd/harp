# Configuration file for the Sphinx documentation builder.

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.abspath(".."))

project = "Harp Proxy"

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
    "sphinx.ext.githubpages",
    "sphinx.ext.graphviz",
    "sphinx.ext.ifconfig",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinx.ext.viewcode",
    "sphinx_copybutton",
    "sphinx_design",
    "sphinx_sitemap",
    "sphinxcontrib.jquery",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

root_doc = "index"

html_theme = "furo"
html_static_path = ["_static"]
html_js_files = ["js/links-target-blank.js"]
html_baseurl = "https://msqd.github.io/harp/"

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
    "python": ("https://docs.python.org/3.12", None),
}
