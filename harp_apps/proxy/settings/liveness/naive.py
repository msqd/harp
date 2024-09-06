from typing import Annotated, Literal, Optional, override

from pydantic import BaseModel, Field

from .base import BaseLiveness, BaseLivenessSettings, LivenessSubject


class NaiveLivenessSettings(BaseLivenessSettings):
    type: Literal["naive"]

    failure_threshold: Annotated[int, Field(gt=0)] = 1
    success_threshold: Annotated[int, Field(gt=0)] = 1

    def build_impl(self):
        return NaiveLiveness(settings=self)


class NaiveLivenessSubjectState(BaseModel):
    """Holds the internal state of the target subject. Will be attached as an attribute to the said subject, but only
    used by the liveness implementation."""

    failure_score: int = 0
    success_score: int = 0


class NaiveLiveness(BaseLiveness[NaiveLivenessSettings]):
    @classmethod
    def get_state_of(cls, subject: LivenessSubject) -> NaiveLivenessSubjectState:
        _attr = f"__{type(cls).__name__}__state__"
        if not hasattr(subject, _attr):
            setattr(subject, _attr, NaiveLivenessSubjectState())
        return getattr(subject, _attr)

    @override
    def success(self, subject: LivenessSubject) -> bool:
        """Returns a boolean indicating if a state change happened."""
        state = self.get_state_of(subject)

        state.success_score += 1
        state.failure_score = 0

        if state.success_score >= self.settings.success_threshold:
            return self.set_status_as_up_if_necessary(subject)

        return False

    @override
    def failure(self, subject: LivenessSubject, reason: Optional[str] = None) -> bool:
        """Returns a boolean indicating if a state change happened."""
        state = self.get_state_of(subject)

        state.success_score = 0
        state.failure_score += 1

        self.add_failure_reason(subject, reason)

        if state.failure_score >= self.settings.failure_threshold:
            return self.set_status_as_down_if_necessary(subject)

        return False
