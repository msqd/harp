from structlog import get_logger

from harp.config import Application, OnBindEvent, OnReadyEvent
from harp_apps.proxy.events import EVENT_PROXY_ERROR, ProxyErrorEvent

from .settings import SentrySettings

logger = get_logger(__name__)


async def on_proxy_error(event: ProxyErrorEvent):
    import sentry_sdk

    sentry_sdk.capture_exception(event.error.exception)


async def on_bind(event: OnBindEvent):
    event.dispatcher.add_listener(EVENT_PROXY_ERROR, on_proxy_error)


def init_sentry(dsn: str, **options):
    import sentry_sdk
    from sentry_sdk.integrations.argv import ArgvIntegration

    sentry_sdk.init(
        dsn=dsn,
        traces_sample_rate=1.0,
        # Secrets travel on the command line (--set storage.url=...) and in local variables of failing frames.
        disabled_integrations=[ArgvIntegration()],
        include_local_variables=False,
        **options,
    )


async def on_ready(event: OnReadyEvent):
    settings = event.provider.get(SentrySettings)
    if not settings.dsn:
        return

    from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

    init_sentry(settings.dsn)
    event.asgi_app = SentryAsgiMiddleware(event.asgi_app)


application = Application(
    on_bind=on_bind,
    on_ready=on_ready,
    settings_type=SentrySettings,
)
