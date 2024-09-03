from whistle import AsyncEventDispatcher

from harp.asgi.events import EVENT_CORE_REQUEST, ControllerEvent


async def on_core_controller(event: ControllerEvent):
    print(f"Controller requested: {event}")


if __name__ == "__main__":
    # for example completeness only, you should use the system dispatcher
    dispatcher = AsyncEventDispatcher()
    dispatcher.add_listener(EVENT_CORE_REQUEST, on_core_controller)
