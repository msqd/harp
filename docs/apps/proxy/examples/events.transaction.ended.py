from whistle import AsyncEventDispatcher

from harp_apps.proxy.events import EVENT_TRANSACTION_ENDED, TransactionEvent


async def on_transaction_ended(event: TransactionEvent):
    print(f"Transaction ended: {event}")


if __name__ == "__main__":
    # for example completeness only, you should use the system dispatcher
    dispatcher = AsyncEventDispatcher()
    dispatcher.add_listener(EVENT_TRANSACTION_ENDED, on_transaction_ended)
