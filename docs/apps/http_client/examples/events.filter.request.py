from whistle import AsyncEventDispatcher

from harp_apps.http_client.events import EVENT_FILTER_HTTP_CLIENT_REQUEST, HttpClientFilterEvent


async def on_filter_request(event: HttpClientFilterEvent):
    print(f"Filtering request: {event}")


if __name__ == "__main__":
    # for example completeness only, you should use the system dispatcher
    dispatcher = AsyncEventDispatcher()
    dispatcher.add_listener(EVENT_FILTER_HTTP_CLIENT_REQUEST, on_filter_request)
