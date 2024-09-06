import time
from typing import Literal, Optional, override

from pydantic import BaseModel

from harp_apps.proxy.settings.liveness.base import BaseLiveness, BaseLivenessSettings, LivenessSubject


class LeakyBucketLivenessSettings(BaseLivenessSettings):
    type: Literal["leaky"]

    #: The rate at which the bucket leaks (x per second).
    rate: float = 1.0

    #: The maximum capacity of the bucket.
    capacity: float = 60.0

    #: The threshold over which the remote is considered down.
    threshold: float = 10.0

    def build_impl(self):
        return LeakyBucketLiveness(settings=self)


class LeakyBucketLivenessSubjectState(BaseModel):
    last_checked: Optional[float] = None
    current: float = 0.0

    def leak(self, rate: float):
        if not self.last_checked:
            self.last_checked = time.time()
        current_time = time.time()
        elapsed_time = current_time - self.last_checked
        self.current = max(0.0, self.current - elapsed_time * rate)
        self.last_checked = current_time


class LeakyBucketLiveness(BaseLiveness[LeakyBucketLivenessSettings]):
    @classmethod
    def get_state_of(cls, subject: LivenessSubject) -> LeakyBucketLivenessSubjectState:
        _attr = f"__{type(cls).__name__}__state__"
        if not hasattr(subject, _attr):
            setattr(subject, _attr, LeakyBucketLivenessSubjectState())
        return getattr(subject, _attr)

    @override
    def success(self, subject: LivenessSubject) -> bool:
        state = self.get_state_of(subject)
        state.leak(self.settings.rate)

        if state.current < self.settings.threshold:
            return self.set_status_as_up_if_necessary(subject)

        return False

    @override
    def failure(self, subject: LivenessSubject, reason: Optional[str] = None) -> bool:
        state = self.get_state_of(subject)
        state.leak(self.settings.rate)
        state.current = min(self.settings.capacity, state.current + 1)

        self.add_failure_reason(subject, reason)

        if state.current >= self.settings.threshold:
            return self.set_status_as_down_if_necessary(subject)

        return False
