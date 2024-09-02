from whistle import AsyncEventDispatcher

from harp_apps.proxy.events import EVENT_TRANSACTION_STARTED, TransactionEvent


async def on_transaction_started(event: TransactionEvent):
    print(f"Transaction started: {event}")


if __name__ == "__main__":
    # for example completeness only, you should use the system dispatcher
    dispatcher = AsyncEventDispatcher()
    dispatcher.add_listener(EVENT_TRANSACTION_STARTED, on_transaction_started)
