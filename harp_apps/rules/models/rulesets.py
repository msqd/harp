from functools import reduce

import orjson

from harp_apps.rules.constants import DEFAULT_LEVELS, DEFAULT_RULES_LEVELS
from harp_apps.rules.models.compilers import BaseRuleSetCompiler


def _match_level(rules, against):
    for pattern, rules in rules:
        if pattern.match(against):
            if hasattr(rules, "items"):
                yield from rules.items()
            else:
                yield from rules


def _rules_as_human_dict(rules: dict, *, show_scripts=True):
    result = {}
    for k, v in rules.items():
        if isinstance(v, dict):
            result[k.source] = _rules_as_human_dict(v, show_scripts=show_scripts)
        else:
            if show_scripts:
                result[k.source] = [script.source.strip() for script in v]
                if len(result[k.source]) == 1:
                    result[k.source] = result[k.source][0]
            else:
                result[k.source] = "..."
    return result


def _recursive_len(rules: dict):
    return reduce(
        lambda x, y: x + _recursive_len(y[1]) if hasattr(y[1], "items") else x + 1,
        rules.items(),
        0,
    )


class BaseRuleSet:
    CompilerType = BaseRuleSetCompiler

    def __init__(self, rules=None, /, *, levels=DEFAULT_LEVELS):
        #: levels: tuple of the rules hierarchy level names
        self._levels = levels

        #: compiler: compiler implementation
        self._compiler = self.CompilerType(levels=levels)

        #: rules: the compiled rules
        self._rules = rules or {}

    @property
    def rules(self):
        return self._rules

    def add(self, sources: dict):
        self._rules = self._compiler.compile(sources, target=self._rules)

    def match(self, *args):
        """
        Match the given arguments against the rules. Each argument must match a "level" in this ruleset.
        """
        if len(args) != len(self._levels):
            raise ValueError(f"Expected {len(self._levels)} arguments, got {len(args)}")

        rules = self.rules.items()
        for against in args:
            rules = _match_level(rules, against)
        yield from rules

    def _asdict(self, /, *, secure=True):
        return _rules_as_human_dict(self.rules)

    def __len__(self):
        return _recursive_len(self.rules)

    def __repr__(self):
        return f"{type(self).__name__}({orjson.dumps(_rules_as_human_dict(self.rules, show_scripts=False)).decode()})"


class RuleSet(BaseRuleSet):
    def __init__(self):
        super().__init__(levels=DEFAULT_RULES_LEVELS)
