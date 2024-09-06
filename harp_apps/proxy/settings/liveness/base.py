from typing import Literal, Optional, Protocol, TypeVar

from pydantic import model_validator

from harp.config import Configurable, Stateful
from harp_apps.proxy.constants import DOWN, UP


class BaseLivenessSettings(Configurable):
    type: Literal["ignore", "inherit", "naive", "leaky"] = "inherit"

    @model_validator(mode="before")
    @classmethod
    def __initialize_type(cls, value):
        _args = cls.model_fields["type"].annotation.__args__
        if len(_args) == 1:
            value.setdefault("type", _args[0])
        return value


class LivenessSubject(Protocol):
    status: int
    failure_reasons: Optional[set]


TSettings = TypeVar("TSettings", bound=Configurable)


class BaseLiveness(Stateful[TSettings]):
    def success(self, subject: LivenessSubject) -> bool:
        raise NotImplementedError()

    def failure(self, subject: LivenessSubject, reason: Optional[str] = None) -> bool:
        raise NotImplementedError()

    def reset_failure_reasons(self, subject: LivenessSubject):
        subject.failure_reasons = None

    def add_failure_reason(self, subject: LivenessSubject, reason: Optional[str] = None):
        if subject.failure_reasons is None:
            subject.failure_reasons = set()
        if reason:
            subject.failure_reasons.add(reason)

    def set_status_as_up_if_necessary(self, subject: LivenessSubject) -> bool:
        """Change the status to UP if it is not already UP, returns whether the state changed."""
        if subject.status != UP:
            self.reset_failure_reasons(subject)
            subject.status = UP
            return True
        return False

    def set_status_as_down_if_necessary(self, subject: LivenessSubject) -> bool:
        """Change the status to DOWN if it is not already DOWN, returns whether the state changed."""
        if subject.status != DOWN:
            subject.status = DOWN
            return True
        return False
