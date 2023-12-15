import asyncio
import sys

from harp import ProxyFactory

proxy = ProxyFactory(args=sys.argv[1:])
proxy.load("harp.contrib.sqlalchemy_storage")

if __name__ == "__main__":
    asyncio.run(proxy.serve())
