from datetime import timedelta

from pydantic import Field

from harp.config import ApplicationSettingsMixin


class AuthSettings(ApplicationSettingsMixin):
    session_idle_hours: int = Field(
        12,
        gt=0,
        description="Hours without a request after which a dashboard session ends. Enforced by the server.",
    )

    session_max_hours: int = Field(
        168,
        gt=0,
        description="Hours after which a dashboard session ends whatever its activity (168 is 7 days). Enforced by "
        "the server.",
    )

    setup_link_hours: int = Field(
        72,
        gt=0,
        description="Hours a setup link stays valid. A new one is made at each start while no Admin exists.",
    )

    @property
    def session_idle(self) -> timedelta:
        return timedelta(hours=self.session_idle_hours)

    @property
    def session_max_age(self) -> timedelta:
        return timedelta(hours=self.session_max_hours)

    @property
    def setup_link_lifetime(self) -> timedelta:
        return timedelta(hours=self.setup_link_hours)
