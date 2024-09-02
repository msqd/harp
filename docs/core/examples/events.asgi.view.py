from whistle import AsyncEventDispatcher

from harp.asgi.events import EVENT_CORE_VIEW, ViewEvent


async def on_core_view(event: ViewEvent):
    print(f"View received: {event}")


if __name__ == "__main__":
    # for example completeness only, you should use the system dispatcher
    dispatcher = AsyncEventDispatcher()
    dispatcher.add_listener(EVENT_CORE_VIEW, on_core_view)
