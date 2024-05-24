"""
The Views (:mod:`harp.views`) package contains tools for transforming non-response controller return values into
responses.

Contents
--------
"""

from .json import json
from .strings import html

__title__ = "Views"

__all__ = [
    "json",
    "html",
]
