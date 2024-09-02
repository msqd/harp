from whistle import AsyncEventDispatcher

from harp.asgi.events import EVENT_CORE_RESPONSE, ResponseEvent


async def on_core_response(event: ResponseEvent):
    print(f"Response received: {event}")


if __name__ == "__main__":
    # for example completeness only, you should use the system dispatcher
    dispatcher = AsyncEventDispatcher()
    dispatcher.add_listener(EVENT_CORE_RESPONSE, on_core_response)
