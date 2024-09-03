from whistle import AsyncEventDispatcher

from harp.config.events import EVENT_BOUND, OnBoundEvent


async def on_bound(event: OnBoundEvent):
    print("System is bound")


if __name__ == "__main__":
    # for example completeness only, you should use the system dispatcher
    dispatcher = AsyncEventDispatcher()
    dispatcher.add_listener(EVENT_BOUND, on_bound)
