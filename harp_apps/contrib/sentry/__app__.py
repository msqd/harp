from harp.config import Application, FactoryBuildEvent

from .settings import SentrySettings


class SentryApplication(Application):
    Settings = SentrySettings

    class Lifecycle:
        @staticmethod
        async def on_build(event: FactoryBuildEvent):
            settings = event.provider.get(SentrySettings)
            if not settings.dsn:
                return

            import sentry_sdk
            from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

            sentry_sdk.init(dsn=settings.dsn, traces_sample_rate=1.0)

            event.kernel = SentryAsgiMiddleware(event.kernel)
