import httpx
from hishel import ParseError
from httpx import RequestNotRead, ResponseNotRead
from rich.console import Console
from rich.padding import Padding
from rich.panel import Panel
from rich.syntax import Syntax

from harp.http import HttpRequestSerializer
from harp.http.serializers import HttpResponseSerializer
from harp.http.utils import parse_cache_control
from harp.utils.strings import truncate_string
from harp.utils.types import typeof
from harp_apps.http_client.events import HttpClientFilterEvent
from harp_apps.proxy.events import ProxyFilterEvent

BODY_MAX_LENGTH_TO_DISPLAY = 4096

console = Console()


async def on_proxy_request_dump(event: ProxyFilterEvent):
    serializer = HttpRequestSerializer(event.request)
    await event.request.aread()
    console.print(
        Panel(
            Syntax(
                "\n".join(
                    (
                        serializer.summary,
                        serializer.headers,
                        truncate_string(serializer.body.decode(), BODY_MAX_LENGTH_TO_DISPLAY),
                    )
                ).strip(),
                "http",
                background_color="default",
            ),
            title=f"[blue]▶[/blue] Request ({typeof(event.request)})",
            title_align="left",
        )
    )


async def on_proxy_response_dump(event: ProxyFilterEvent):
    serializer = HttpResponseSerializer(event.response)
    await event.response.aread()
    console.print(
        Panel(
            Syntax(
                "\n".join(
                    (
                        serializer.summary,
                        serializer.headers,
                        truncate_string(serializer.body.decode(), BODY_MAX_LENGTH_TO_DISPLAY),
                    )
                ).strip(),
                "http",
                background_color="default",
            ),
            title=f"[green]◀[/green] Proxy Response ({typeof(event.response)})",
            title_align="left",
        )
    )


def dump_httpx_request(request: httpx.Request) -> str:
    # Convert the request headers to a string
    headers_str = "\n".join(f"{name}: {value}" for name, value in request.headers.items())

    # Access the request body; for non-streaming bodies, you can directly use request.content
    # For streaming bodies, you might need to handle them differently depending on your use case
    try:
        body_str = request.content.decode("utf-8") if request.content else ""
    except RequestNotRead:
        body_str = ""
    body_str = truncate_string(body_str, BODY_MAX_LENGTH_TO_DISPLAY)

    # Combine method, URL, headers, and body into a formatted string
    request_dump = f"{request.method} {request.url.raw_path.decode()} HTTP/1.1\n{headers_str}\n\n{body_str}"

    return request_dump.strip()


def dump_httpx_response(response: httpx.Response) -> str:
    # Convert the response headers to a string
    headers_str = "\n".join(f"{name}: {value}" for name, value in response.headers.items())

    # Access the response body; for non-streaming bodies, you can directly use response.content
    # For streaming bodies, you might need to handle them differently depending on your use case
    try:
        body_str = response.text
    except ResponseNotRead:
        body_str = ""
    body_str = truncate_string(body_str, BODY_MAX_LENGTH_TO_DISPLAY)

    # Combine status code, headers, and body into a formatted string
    response_dump = (
        f"{response.http_version} {response.status_code} {response.reason_phrase}\n{headers_str}\n\n{body_str}"
    )

    return response_dump.strip()


async def on_remote_request_dump(event: HttpClientFilterEvent):
    console.print(
        Padding(
            Panel(
                Syntax(
                    dump_httpx_request(event.request),
                    "http",
                    background_color="default",
                ),
                title=f"[blue]▶▶[/blue] Remote Request ({typeof(event.request)})",
                title_align="left",
            ),
            (0, 0, 0, 4),
        )
    )


async def on_remote_response_dump(event: HttpClientFilterEvent):
    console.print(
        Padding(
            Panel(
                Syntax(
                    dump_httpx_response(event.response),
                    "http",
                    background_color="default",
                ),
                title=f"[green]◀◀[/green] Remote Response ({typeof(event.response)})",
                title_align="left",
            ),
            (0, 0, 0, 4),
        )
    )


async def on_remote_response_show_cache_control(event: HttpClientFilterEvent):
    response = event.response
    cache_control = response.headers.get_list("Cache-Control")
    if cache_control:
        try:
            parsed_cached_control = parse_cache_control(cache_control)
        except ParseError as exc:
            parsed_cached_control = exc

        console.print(
            Padding(
                Panel(
                    Syntax(
                        f"{typeof(parsed_cached_control, short=True)}: {parsed_cached_control}",
                        "http",
                        background_color="default",
                    ),
                    title="[green]◀◀[/green] Cache Control",
                    title_align="left",
                ),
                (0, 0, 0, 8),
            )
        )
