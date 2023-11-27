import asyncio

from asgi_tools import App
from hypercorn.asyncio import serve
from hypercorn.config import Config

from harp.testing.network_utils import get_available_network_port

app = App()


@app.route("/")
async def hello_world(request):
    return "<p>Hello, World!</p>"


shutdown_event = asyncio.Event()


async def start_server():
    port = get_available_network_port()
    config = Config()
    config.bind = [f"0.0.0.0:{port}"]

    try:
        await serve(app, config, shutdown_trigger=shutdown_event.wait)
    except Exception:
        shutdown_event.set()


def main():
    loop = asyncio.get_event_loop()
    task = asyncio.ensure_future(start_server(), loop=loop)
    loop.run_until_complete(asyncio.sleep(1))

    for i in range(3):
        loop.run_until_complete(asyncio.sleep(1))
        print(task)
    shutdown_event.set()
    loop.run_until_complete(task)

    # anyio.run(serve, app, config, backend="asyncio", backend_options={"use_uvloop": True})


if __name__ == "__main__":
    main()
