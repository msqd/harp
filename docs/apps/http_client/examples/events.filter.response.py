from whistle import AsyncEventDispatcher

from harp_apps.http_client.events import EVENT_FILTER_HTTP_CLIENT_RESPONSE, HttpClientFilterEvent


async def on_filter_response(event: HttpClientFilterEvent):
    print(f"Filtering response: {event}")


if __name__ == "__main__":
    # for example completeness only, you should use the system dispatcher
    dispatcher = AsyncEventDispatcher()
    dispatcher.add_listener(EVENT_FILTER_HTTP_CLIENT_RESPONSE, on_filter_response)
