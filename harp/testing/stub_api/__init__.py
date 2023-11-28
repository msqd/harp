from asgi_tools import App

stub_api = App()


@stub_api.route("/echo")
async def echo(request):
    return f"{request.method} {request.url.path}"


@stub_api.route("/echo/body", methods=["POST", "PUT", "PATCH"])
async def echo_body(request):
    body = await request.body()
    return f"{request.method} {request.url.path}\n{repr(body)}"
