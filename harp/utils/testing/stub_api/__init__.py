import os

from asgi_tools import App, Response

stub_api = App()


@stub_api.route("/echo")
async def echo(request):
    return f"{request.method} {request.url.path}"


@stub_api.route("/headers")
async def headers(request):
    return Response(b"", headers={"X-Foo": "Bar"}, content_type="application/octet-stream")


@stub_api.route("/status/{status}")
async def status(request):
    status_code = int(request.path_params["status"])

    return Response(b"", status_code=status_code)


@stub_api.route("/echo/body", methods=["POST", "PUT", "PATCH"])
async def echo_body(request):
    body = await request.body()
    return f"{request.method} {request.url.path}\n{repr(body)}"


@stub_api.route("/binary", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"])
async def binary(request):
    return Response(os.urandom(32), content_type="application/octet-stream")
