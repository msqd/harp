from datetime import timedelta

from pydantic import Field

from harp.config import ApplicationSettingsMixin


class JanitorSettings(ApplicationSettingsMixin):
    #: How many seconds to wait between loop executions.
    period: int = Field(600, gt=0, description="Seconds to wait between two janitor sweeps.")

    #: Number of days after we consider something as "old".
    old_after: int = Field(60, gt=0, description="Age in days after which transactions are deleted.")

    @property
    def old_after_delta(self) -> timedelta:
        return timedelta(days=self.old_after)
