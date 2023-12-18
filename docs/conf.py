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
release = ".".join(__import__("harp").__version__.split(".")[0:2])

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.githubpages",
    "sphinx.ext.todo",
    "sphinx_design",
    "sphinxcontrib.jquery",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

root_doc = "index"

html_theme = "furo"
html_static_path = ["_static"]
html_js_files = ["js/links-target-blank.js"]

todo_include_todos = True
html_show_sphinx = False
