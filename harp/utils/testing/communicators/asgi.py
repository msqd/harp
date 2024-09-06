from asgiref.typing import ASGIApplication, LifespanScope, LifespanStartupEvent


class ASGICommunicator:
    default_host = "localhost"
    default_port = 80

    def __init__(self, asgi_app: ASGIApplication, *, default_host=None, default_port=None):
        self.asgi_app = asgi_app
        self.default_host = default_host or self.default_host
        self.default_port = default_port or self.default_port

    async def asgi_lifespan_startup(self):
        from asgiref.testing import ApplicationCommunicator

        com = ApplicationCommunicator(
            self.asgi_app,
            LifespanScope(
                type="lifespan",
                asgi={
                    "spec_version": "2.1",
                    "version": "3.0",
                },
            ),
        )
        await com.send_input(
            LifespanStartupEvent(type="lifespan.startup"),
        )
        await com.wait()

    def http_request(self, method, path, *, body=b"", headers=None, host=None, port=None):
        from harp.utils.testing.communicators import HTTPCommunicator

        communicator = HTTPCommunicator(
            self.asgi_app,
            method,
            path,
            body=body,
            headers=headers,
            hostname=host or self.default_host,
            port=port or self.default_port,
        )

        return communicator.get_response()

    def http_get(self, path, *, headers=None, host=None, port=None):
        return self.http_request("GET", path, headers=headers, host=host, port=port)

    def http_post(self, path, *, body=b"", headers=None, host=None, port=None):
        return self.http_request("POST", path, body=body, headers=headers, host=host, port=port)

    def http_put(self, path, *, headers=None, host=None, port=None):
        return self.http_request("PUT", path, headers=headers, host=host, port=port)

    def http_patch(self, path, *, headers=None, host=None, port=None):
        return self.http_request("PATCH", path, headers=headers, host=host, port=port)

    def http_delete(self, path, *, headers=None, host=None, port=None):
        return self.http_request("DELETE", path, headers=headers, host=host, port=port)

    def http_options(self, path, *, headers=None, host=None, port=None):
        return self.http_request("OPTIONS", path, host=host, port=port)

    def http_head(self, path, *, headers=None, host=None, port=None):
        return self.http_request("HEAD", path, headers=headers, host=host, port=port)
