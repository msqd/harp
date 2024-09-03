from whistle import AsyncEventDispatcher

from harp_apps.proxy.events import EVENT_TRANSACTION_MESSAGE, HttpMessageEvent


async def on_transaction_message(event: HttpMessageEvent):
    print(f"Transaction message: {event}")


if __name__ == "__main__":
    # for example completeness only, you should use the system dispatcher
    dispatcher = AsyncEventDispatcher()
    dispatcher.add_listener(EVENT_TRANSACTION_MESSAGE, on_transaction_message)
