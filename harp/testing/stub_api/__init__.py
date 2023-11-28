from asgi_tools import App

stub_api = App()


@stub_api.route("/echo", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
async def echo(request):
    return f"{request.method} {request.url.path}"
