from typing import Annotated, Union

from pydantic import Discriminator

from .ignore import IgnoreLiveness, IgnoreLivenessSettings
from .inherit import InheritLiveness, InheritLivenessSettings
from .leaky_bucket import LeakyBucketLiveness, LeakyBucketLivenessSettings
from .naive import NaiveLiveness, NaiveLivenessSettings

LivenessSettings = Annotated[
    Union[
        IgnoreLivenessSettings,
        InheritLivenessSettings,
        LeakyBucketLivenessSettings,
        NaiveLivenessSettings,
    ],
    Discriminator("type"),
]

Liveness = Union[
    IgnoreLiveness,
    InheritLiveness,
    LeakyBucketLiveness,
    NaiveLiveness,
]
