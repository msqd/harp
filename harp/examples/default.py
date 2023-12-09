import asyncio
import sys

from harp import ProxyFactory

proxy = ProxyFactory(
    settings={
        "storage": {
            "type": "sqlalchemy",
            "url": "sqlite+aiosqlite:///customized.db",
            "echo": False,
            "drop_tables": True,
        }
    },
    args=sys.argv[1:],
)
proxy.load("harp.contrib.sqlalchemy_storage")

if __name__ == "__main__":
    asyncio.run(proxy.serve())
