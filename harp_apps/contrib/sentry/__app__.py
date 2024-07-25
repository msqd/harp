from harp.config import Application, OnReadyEvent

from .settings import SentrySettings


async def on_ready(event: OnReadyEvent):
    settings = event.provider.get(SentrySettings)
    if not settings.dsn:
        return

    import sentry_sdk
    from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

    sentry_sdk.init(dsn=settings.dsn, traces_sample_rate=1.0)
    event.kernel = SentryAsgiMiddleware(event.kernel)


application = Application(
    on_ready=on_ready,
    settings_type=SentrySettings,
)
