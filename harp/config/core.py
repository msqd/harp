from pydantic import Field

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
