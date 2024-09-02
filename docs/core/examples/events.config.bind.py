from whistle import AsyncEventDispatcher

from harp.config.events import EVENT_BIND, OnBindEvent


async def on_bind(event: OnBindEvent):
    print("System is being bound")


if __name__ == "__main__":
    # for example completeness only, you should use the system dispatcher
    dispatcher = AsyncEventDispatcher()
    dispatcher.add_listener(EVENT_BIND, on_bind)
