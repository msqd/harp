from typing import Literal

from .base import BaseLiveness, BaseLivenessSettings


class InheritLivenessSettings(BaseLivenessSettings):
    type: Literal["inherit"] = "inherit"


class InheritLiveness(BaseLiveness[InheritLivenessSettings]):
    """This is a placeholder for inheriting liveness, the parent stateful object will replace it. We do not need to
    implement the BaseLiveness interface, as it won't exist anymore once everything is setup."""

    settings: InheritLivenessSettings
