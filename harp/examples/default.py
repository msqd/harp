import asyncio

from harp import ProxyFactory

proxy = ProxyFactory()
proxy.load("harp.contrib.sqlalchemy_storage")

if __name__ == "__main__":
    asyncio.run(proxy.serve())
