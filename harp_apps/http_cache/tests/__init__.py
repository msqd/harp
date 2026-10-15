import httpx


async def _name_endpoint(request: httpx.Request) -> None:
    request.extensions.setdefault("harp", {"endpoint": "test-endpoint"})


#: ``event_hooks`` for test clients: the cache transport requires the endpoint name the proxy sets.
ENDPOINT_HOOKS = {"request": [_name_endpoint]}
