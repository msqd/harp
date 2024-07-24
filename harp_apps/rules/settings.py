from harp_apps.rules.models.rulesets import RuleSet


class RulesSettings:
    def __init__(self, /, **sources):
        self.rules = RuleSet()
        self.rules.add(sources)

    def _asdict(self, /, *, secure=True):
        return self.rules._asdict(secure=secure)

    def __repr__(self):
        return f"{self.__class__.__name__}(rules={self.rules})"

    def load(self, /, filename, *, prefix="rules"):
        if filename.endswith(".yaml") or filename.endswith(".yml"):
            from harp.utils.config import yaml

            self.rules.add(yaml.load(filename).get(prefix, {}))
        elif filename.endswith(".toml"):
            from harp.utils.config import toml

            self.rules.add(toml.load(filename).get(prefix, {}))
        else:
            raise ValueError(f"Unsupported file format: {filename}")
