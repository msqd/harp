from whistle import AsyncEventDispatcher

from harp_apps.proxy.events import EVENT_FILTER_PROXY_REQUEST, ProxyFilterEvent


async def on_filter_request(event: ProxyFilterEvent):
    print(f"Filtering request: {event}")


if __name__ == "__main__":
    # for example completeness only, you should use the system dispatcher
    dispatcher = AsyncEventDispatcher()
    dispatcher.add_listener(EVENT_FILTER_PROXY_REQUEST, on_filter_request)
