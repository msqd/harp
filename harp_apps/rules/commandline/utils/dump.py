import httpx
from httpx import ResponseNotRead
from rich.console import Console
from rich.padding import Padding
from rich.panel import Panel
from rich.syntax import Syntax

from harp.http import HttpRequestSerializer
from harp.http.serializers import HttpResponseSerializer

console = Console(force_terminal=True)


def typeof(x):
    return f"{type(x).__module__}.{type(x).__qualname__}"


async def on_proxy_request_dump(event):
    serializer = HttpRequestSerializer(event.request)
    await event.request.join()
    console.print(
        Panel(
            Syntax(
                "\n".join((serializer.summary, serializer.headers, serializer.body.decode())).strip(),
                "http",
                background_color="default",
            ),
            title=f"[blue]▶[/blue] [bright_white]Request[/bright_white] ({typeof(event.request)})",
            title_align="left",
        )
    )


async def on_proxy_response_dump(event):
    serializer = HttpResponseSerializer(event.response)
    await event.response.join()
    console.print(
        Panel(
            Syntax(
                "\n".join((serializer.summary, serializer.headers, serializer.body.decode())).strip(),
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
    body_str = request.content.decode("utf-8") if request.content else ""

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

    # Combine status code, headers, and body into a formatted string
    response_dump = (
        f"{response.http_version} {response.status_code} {response.reason_phrase}\n{headers_str}\n\n{body_str}"
    )

    return response_dump.strip()


async def on_remote_request_dump(event):
    console.print(
        Padding(
            Panel(
                Syntax(dump_httpx_request(event.request), "http", background_color="default"),
                title=f"[blue]▶▶[/blue] Remote Request ({typeof(event.request)})",
                title_align="left",
            ),
            (0, 0, 0, 4),
        )
    )


async def on_remote_response_dump(event):
    console.print(
        Padding(
            Panel(
                Syntax(dump_httpx_response(event.response), "http", background_color="default"),
                title=f"[green]◀◀[/green] Remote Response ({typeof(event.response)})",
                title_align="left",
            ),
            (0, 0, 0, 4),
        )
    )
