from asgi_tools import App

stub_api = App()


@stub_api.route("/echo")
async def echo(request):
    return f"{request.method} {request.url.path}"
