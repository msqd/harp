from whistle import AsyncEventDispatcher, Event

from harp.asgi.events import EVENT_CORE_STARTED


async def on_core_started(event: Event):
    print(f"ASGI Core started: {event}")


if __name__ == "__main__":
    # for example completeness only, you should use the system dispatcher
    dispatcher = AsyncEventDispatcher()
    dispatcher.add_listener(EVENT_CORE_STARTED, on_core_started)
