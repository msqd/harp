from harp.config import Application, OnBindEvent
from harp_apps.services.definitions.database import register_database_service
from harp_apps.services.definitions.redis import register_redis_service
from harp_apps.services.settings import ServicesSettings


async def on_bind(event: OnBindEvent):
    settings: ServicesSettings = event.settings["services"]
    container = event.container

    if settings.redis:
        register_redis_service(container, settings.redis)

    if settings.database:
        register_database_service(container, settings.database)


application = Application(on_bind=on_bind, settings_type=ServicesSettings)
