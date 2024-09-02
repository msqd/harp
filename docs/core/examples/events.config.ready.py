from whistle import AsyncEventDispatcher

from harp.config.events import EVENT_READY, OnReadyEvent


async def on_ready(event: OnReadyEvent):
    print("System is ready")


if __name__ == "__main__":
    # for example completeness only, you should use the system dispatcher
    dispatcher = AsyncEventDispatcher()
    dispatcher.add_listener(EVENT_READY, on_ready)
