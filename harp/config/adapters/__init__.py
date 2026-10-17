from dataclasses import dataclass

from harp.config.adapters.granian import GranianAdapter
from harp.config.adapters.hypercorn import HypercornAdapter
from harp.config.adapters.uvicorn import UvicornAdapter


@dataclass(frozen=True)
class Server:
    """An ASGI server HARP can run on: the adapter that serves the system, and whether the loop must be uvloop."""

    adapter_type: type
    uvloop: bool = False


_SERVERS = {
    "hypercorn": Server(HypercornAdapter),
    "hypercorn+uvloop": Server(HypercornAdapter, uvloop=True),
    "uvicorn": Server(UvicornAdapter, uvloop=True),
    "granian": Server(GranianAdapter),
}

SERVERS = tuple(_SERVERS)
DEFAULT_SERVER = "hypercorn"


def get_server(name: str) -> Server:
    try:
        return _SERVERS[name]
    except KeyError:
        raise ValueError(f"Unknown server {name!r}, choose one of: {', '.join(SERVERS)}.") from None
