from urllib.parse import urljoin

import httpx
import uvicorn
import rich, rich.panel, rich.pretty, rich.text


class Filter():
    def __rshift__(self, other):
        """ self >> other """
        pass

    def __irshift__(self, other):
        """ other >> self """
        pass


class Harp():
    def __init__(self):
        self.default_ingress = Filter()
        self.ingresses = [self.default_ingress]
        self.rules = []
        self.mounts = []

    def add_egress(self, endpoint):
        return Filter()

    def add_rule(self, rule):
        self.rules.append(rule)

    def mount(self, prefix, target, *, scope_filters=(), request_filters = (), response_filters = ()):
        prefix_length = len(prefix) - 1
        async def _mount_scope_filter(scope):
            scope['remote_path'] = scope['path'][prefix_length:]
        self.mounts.append((prefix, target, (_mount_scope_filter, *scope_filters), request_filters, response_filters ))

    def find_by_scope(self, scope):
        for prefix, target, scope_filters, request_filters, response_filters in self.mounts:
            if scope['path'].startswith(prefix):
                return target, scope_filters, request_filters, response_filters
        return None, (), (), ()

    def run(self):
        uvicorn.run(get_asgi_app_for_router(self), port=5000, log_level="info", headers=[('server', 'harp/0.1')])


client = httpx.AsyncClient(timeout=10.0, )

USE_STREAMING=False

def get_asgi_app_for_router(router: Harp):
    async def _asgi_app(scope, receive, send):
        if scope['scheme'] != 'http':
            return

        target_url, scope_filters, request_filters, response_filters = router.find_by_scope(scope)

        if not target_url:
            await send({
                'type': 'http.response.start',
                'status': 404,
            })
            await send({
                'type': 'http.response.body',
                'body': bytes(f'No handler found for path "{scope["path"]}".', 'utf-8'),
            })
            return

        for scope_filter in scope_filters:
            await scope_filter(scope)

        #rich.print(rich.panel.Panel(rich.pretty.Pretty(scope), title="ASGI Scope", title_align="left"))

        response: httpx.Response

        if USE_STREAMING:
            async with client.stream(scope['method'], urljoin(target_url, scope["remote_path"])) as response:
                # rich.print(rich.panel.Panel(rich.pretty.Pretty(dict(response.headers)), title="Response Headers (remote)", title_align="left"))

                await send({
                    'type': 'http.response.start',
                    'status': response.status_code,
                    'headers': [(k, v) for k, v in response.headers.raw if k.lower() not in (b'server', b'date')],
                })

                async for chunk in response.aiter_bytes():
                    await send({
                        'type': 'http.response.body',
                        'body': chunk,
                        'more_body': True
                    })

                await send({
                    'type': 'http.response.body',
                    'body': b'',
                })
        else:
            response = await client.request(scope['method'], urljoin(target_url, scope["remote_path"]))
            # rich.print(rich.panel.Panel(rich.pretty.Pretty(dict(response.headers)), title="Response Headers (remote)", title_align="left"))

            await send({
                'type': 'http.response.start',
                'status': response.status_code,
                'headers': [(k, v) for k, v in response.headers.raw if k.lower() not in (b'server', b'date')],
            })

            await send({
                'type': 'http.response.body',
                'body': response.content,
            })

    return _asgi_app
