from typing import Literal, Optional, override

from .base import BaseLiveness, BaseLivenessSettings, LivenessSubject


class IgnoreLivenessSettings(BaseLivenessSettings):
    type: Literal["ignore"]

    def build_impl(self):
        return IgnoreLiveness(settings=self)


class IgnoreLiveness(BaseLiveness[IgnoreLivenessSettings]):
    @override
    def success(self, subject: LivenessSubject) -> bool:
        return False

    @override
    def failure(self, subject: LivenessSubject, reason: Optional[str] = None):
        return False
