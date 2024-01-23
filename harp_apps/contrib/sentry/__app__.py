from harp.config import Application
from harp.config.events import FactoryBuildEvent

from .settings import SentrySettings


class SentryApplication(Application):
    settings_namespace = "sentry"
    settings_type = SentrySettings

    @classmethod
    def defaults(cls, settings=None):
        return settings if settings is not None else {"dsn": None}

    async def on_build(self, event: FactoryBuildEvent):
        if not self.settings.dsn:
            return

        import sentry_sdk
        from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

        sentry_sdk.init(
            dsn=self.settings.dsn,
            traces_sample_rate=1.0,
        )

        event.kernel = SentryAsgiMiddleware(event.kernel)
