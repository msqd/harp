from dataclasses import asdict, dataclass

settings_dataclass = dataclass


@settings_dataclass
class BaseSetting:
    def to_dict(self):
        return asdict(self)
