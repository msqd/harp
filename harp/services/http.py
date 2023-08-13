import httpx

client = httpx.AsyncClient(
    timeout=10.0,
)
