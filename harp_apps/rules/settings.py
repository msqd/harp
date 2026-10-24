from harp_apps.rules.models.rulesets import RuleSet
from harp_apps.rules.subscribers import DEFAULT_TIME_BUDGET


class RulesSettings:
    def __init__(self, /, *, time_budget: float = DEFAULT_TIME_BUDGET, **sources):
        #: Seconds a rule script may run, see :class:`RulesSubscriber`. Not usable as an endpoint pattern.
        self.time_budget = time_budget
        self.ruleset = RuleSet()
        self.ruleset.add(sources)

    def _asdict(self, /, *, secure=True):
        rules = self.ruleset._asdict(secure=secure)
        if self.time_budget != DEFAULT_TIME_BUDGET:
            rules["time_budget"] = self.time_budget
        return rules

    def __repr__(self):
        return f"{self.__class__.__name__}(rules={self.ruleset})"

    def load(self, /, filename, *, prefix="rules"):
        if filename.endswith(".yaml") or filename.endswith(".yml"):
            from harp.utils.config import yaml

            self.ruleset.add(yaml.load(filename).get(prefix, {}))
        elif filename.endswith(".toml"):
            from harp.utils.config import toml

            self.ruleset.add(toml.load(filename).get(prefix, {}))
        else:
            raise ValueError(f"Unsupported file format: {filename}")
