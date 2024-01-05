import hishel
import httpx

transport = httpx.AsyncHTTPTransport()
cache_transport = hishel.AsyncCacheTransport(transport=transport)

client = httpx.AsyncClient(
    timeout=10.0,
    transport=cache_transport,
)
