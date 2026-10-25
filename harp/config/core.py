from pydantic import Field, field_validator

from .configurables.base import Configurable


class CoreSettings(Configurable):
    """
    The settings of the core, read from the ``core`` section of the configuration: what belongs to no application.

    Unlike an application's settings, they are always there: the section cannot be disabled, and holds no ``enabled``.
    """

    muted_events: list[str] = Field(
        default_factory=list,
        description="Ids of the loggable events not to write to the event log. Only a loggable event can be named.",
    )

    @field_validator("muted_events", mode="before")
    @classmethod
    def _split_comma_separated(cls, value):
        """Environment variables hold strings: ``HARP_CORE__MUTED_EVENTS=a.b,c.d``."""
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value
