import httpx


async def _name_endpoint(request: httpx.Request) -> None:
    request.extensions.setdefault("harp", {"endpoint": "test-endpoint"})


#: ``event_hooks`` for test clients: the cache transport requires the endpoint name the proxy sets.
ENDPOINT_HOOKS = {"request": [_name_endpoint]}


async def store_entry(storage, request, response, key: str):
    """Create a cache entry and read its body to the end, as a client would: the storage keeps it only then."""
    entry = await storage.create_entry(request, response, key)
    await entry.response.aread()
    return entry
