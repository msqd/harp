import ast
import re


def _to_rule_regex(pattern):
    if pattern.startswith("=~ "):
        return re.compile(pattern[3:])
    return re.compile("^" + ".*".join([re.escape(x) for x in pattern.split("*")]) + "$")


def _match_level(rules, against):
    for pattern, rules in rules:
        if pattern.match(against):
            if hasattr(rules, "items"):
                yield from rules.items()
            else:
                yield from rules


class RuleSet:
    def __init__(self, sources: dict, /, *, levels=("default",)):
        self.rules = None
        self._sources = sources
        self._levels = levels
        self.compile()

    @property
    def sources(self):
        return self._sources

    def _compile_rule_list(self, source: list, *, level=0):
        rules = []
        normalized = []
        for stmt in source:
            code_ast = ast.parse(stmt)
            code = compile(code_ast, filename=f"<rules:{self._index}>", mode="exec")
            rules.append(code)
            for node in code_ast.body:
                unparsed = ast.unparse(node)
                normalized.append(unparsed)
            self._index += 1
        return rules, normalized

    def _compile_rule_dict(self, source: dict, *, level=0, levels=()):
        rules = {}
        normalized = {}
        if not len(levels):
            raise ValueError("No more rule level available.")
        current_level, *levels = levels
        for key, value in source.items():
            _regex = _to_rule_regex(key)
            if isinstance(value, list):
                rules[_regex], normalized[f"=~ {_regex.pattern}"] = self._compile_rule_list(value, level=level + 1)
            elif isinstance(value, dict):
                rules[_regex], normalized[f"=~ {_regex.pattern}"] = self._compile_rule_dict(
                    value, level=level + 1, levels=levels
                )
            else:
                raise ValueError(f"Invalid value type for key {key}: {type(value)}")
        return rules, normalized

    def compile(self):
        self._index = 0
        self.rules, self._sources = self._compile_rule_dict(self._sources, levels=self._levels)

    def match(self, *args):
        if self.rules is None:
            raise RuntimeError("Rules not compiled.")

        if len(args) != len(self._levels):
            raise ValueError(f"Expected {len(self._levels)} arguments, got {len(args)}")

        rules = self.rules.items()
        for against in args:
            rules = _match_level(rules, against)
        yield from rules
