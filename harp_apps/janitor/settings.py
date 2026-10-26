from pydantic import Field

from harp.config import ApplicationSettingsMixin


class JanitorSettings(ApplicationSettingsMixin):
    #: How many seconds to wait between loop executions.
    period: int = Field(600, gt=0, description="Seconds to wait between two janitor sweeps.")

    #: Deprecated alias of ``storage.retention_days``, applied when the configuration is built.
    old_after: int | None = Field(
        None,
        gt=0,
        description="Deprecated, use ``storage.retention_days``. Age in days after which transactions are deleted.",
    )
