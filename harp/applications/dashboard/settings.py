from dataclasses import dataclass


@dataclass(frozen=True)
class DashboardSettings:
    enabled: bool = True
    port: int | str = 4080
    auth: str | None = None
