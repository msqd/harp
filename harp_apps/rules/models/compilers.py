from typing import Callable

from harp_apps.rules.constants import DEFAULT_LEVELS
from harp_apps.rules.models.patterns import Pattern
from harp_apps.rules.models.scripts import ExecutableObject, Script


class BaseRuleSetCompiler:
    def __init__(self, /, *, levels=DEFAULT_LEVELS):
        #: index: internal index to generate unique rule names
        self._index = 0

        #: levels: tuple of hierarchical level names
        self._levels = levels

    @property
    def levels(self):
        return self._levels

    @classmethod
    def compile_pattern(cls, level: str, pattern: str):
        return Pattern(pattern)

    def compile_scripts(self, source: list | str | Callable, /, *, level=0):
        # only one script? let's work on it as a (one item) list anyway.
        if isinstance(source, str) or callable(source):
            source = [source]

        for raw_source in source:
            if callable(raw_source):
                yield ExecutableObject(raw_source)
            else:
                yield Script(raw_source, filename=f"<rule:{self._index}>")
                self._index += 1

    def compile(self, source: dict, /, *, target: dict | None = None, level=0, _levels=None):
        """
        Recursively compile a dictionary of rules.

        { pattern: ... } where "..." can be another dict or a sequence of scripts (str, list of str or other things we
        decide can be executed (maybe strings are only a shortcut for {type: script, src: ...}, we may want to have an
        extended dict base syntax later that can use custom implementations)).

        """
        #: target: target dict to store the compiled rules, allowing the parent to pass ana already partial ruleset,
        #:         which is required for multi-files ruleset compilation.
        target = target or {}

        # what level are we compiling for? what's remaining?
        if _levels is None:
            _levels = self._levels
        if not len(_levels):
            raise ValueError("No more rule level available.")
        current_level, *remaining_levels = _levels

        # iterate over the source dict, a mapping between patterns and either more sources (recursive) or scripts if
        # we are at the last level.
        for key, value in source.items():
            _pattern = self.compile_pattern(current_level, key)

            # are we at the last level? then we should compile scripts
            if not remaining_levels:
                if isinstance(value, (list, str)) or callable(value):
                    if _pattern not in target:
                        target[_pattern] = []
                    target[_pattern].extend(self.compile_scripts(value, level=level + 1))
                else:
                    raise ValueError("Last level of rules dict must be a list of scripts or a single script.")

            # otherwise, we should compile the next level
            elif isinstance(value, dict):
                if _pattern not in target:
                    target[_pattern] = {}

                target[_pattern] = self.compile(
                    value,
                    target=target[_pattern],
                    level=level + 1,
                    _levels=remaining_levels,
                )

            else:
                raise ValueError(f"Invalid value type for key {key}: {type(value)}")

        return target
