import asyncio

from rodi import Container, ServiceLifeStyle
from whistle import AsyncEventDispatcher, IAsyncEventDispatcher

from harp.services.containers import ServiceResolver
from harp.services.models import ServiceCollection


async def main():
    container = Container()
    dispatcher = AsyncEventDispatcher()
    container.add_instance(dispatcher, IAsyncEventDispatcher)
    collection = ServiceCollection.model_validate_yaml("../harp_apps/http_client/services.yml")

    for service in collection:
        resolver = ServiceResolver(container, service, ServiceLifeStyle.SINGLETON)
        container._map[resolver.base_type] = resolver
        container.set_alias(service.name, resolver.base_type)

    provider = container.build_provider()

    client = provider.get("http_client")
    assert client is provider.get("http_client"), "singleton should exist only once per provider"
    print(client)

    async with client:
        response = await client.get("https://api1-internal.harp.demo/cache/5")
        print(response.status_code, response.extensions)
        response = await client.get("https://api1-internal.harp.demo/cache/5")
        print(response.status_code, response.extensions)


if __name__ == "__main__":
    asyncio.run(main())
