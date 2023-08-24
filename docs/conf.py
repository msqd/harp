# Configuration file for the Sphinx documentation builder.

from datetime import datetime

project = "Harp Proxy"

first_year, current_year = 2023, datetime.now().year
author = "Romain Dorgueil"
copyright = f"{current_year}, {author}"
if current_year > first_year:
    copyright = str(first_year) + "-" + copyright
release = "1.0"

extensions = [
    "sphinx_design",
    "sphinxcontrib.jquery",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

root_doc = "index"

html_theme = "furo"
html_static_path = ["_static"]
html_js_files = ["js/links-target-blank.js"]
