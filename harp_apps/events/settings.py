from pydantic import Field

from harp.config import ApplicationSettingsMixin


class EventsSettings(ApplicationSettingsMixin):
    muted: list[str] = Field(
        default_factory=list,
        description="Ids of the loggable events not to write to the event log. Only a loggable event can be named.",
    )
