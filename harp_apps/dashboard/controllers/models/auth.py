from pydantic import BaseModel, ConfigDict


class _Input(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class SignInInput(_Input):
    username: str
    password: str


class SetupInput(_Input):
    secret: str
    username: str
    password: str


class ChangePasswordInput(_Input):
    current: str
    new: str


class NoInput(_Input):
    """Routes that need nothing still take a JSON body (``{}``), which is what keeps a cross-site form out."""
