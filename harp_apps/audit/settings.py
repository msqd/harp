from datetime import timedelta

from pydantic import Field

from harp.config import ApplicationSettingsMixin


class AuditSettings(ApplicationSettingsMixin):
    retention_days: int = Field(
        365,
        gt=0,
        description="Age in days after which the janitor deletes audit events. Longer keeping is the SIEM's job.",
    )

    @property
    def retention(self) -> timedelta:
        return timedelta(days=self.retention_days)
