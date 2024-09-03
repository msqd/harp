from whistle import AsyncEventDispatcher

from harp.config.events import EVENT_SHUTDOWN, OnShutdownEvent


async def on_shutdown(event: OnShutdownEvent):
    print("System is shutting down")


if __name__ == "__main__":
    dispatcher = AsyncEventDispatcher()
    dispatcher.add_listener(EVENT_SHUTDOWN, on_shutdown)
