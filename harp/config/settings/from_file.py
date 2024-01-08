import os

from .base import BaseSetting, settings_dataclass


@settings_dataclass
class FromFileSetting(BaseSetting):
    from_file: str

    @classmethod
    def may_override(cls, instance, attr):
        _value = getattr(instance, attr)
        if not isinstance(_value, dict) or tuple(_value.keys()) != ("fromFile",):
            return
        object.__setattr__(instance, attr, FromFileSetting(from_file=_value["fromFile"]))

    def exists(self):
        return os.path.exists(self.from_file) and os.path.isfile(self.from_file)

    def open(self, *args, **kwargs):
        return open(self.from_file, *args, **kwargs)
