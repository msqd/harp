from harp.config import BaseSetting, settings_dataclass

from .models.ruleset import RuleSet


@settings_dataclass
class RulesSettings(BaseSetting):
    def __init__(self, **sources):
        self.rules = RuleSet(sources, levels=("endpoint", "request", "event"))

    def _asdict(self, /, *, secure=True):
        return self.rules.sources
