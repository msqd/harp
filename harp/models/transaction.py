from dataclasses import dataclass, field
from datetime import datetime

from .message import Request, Response
from .proxy_endpoint import ProxyEndpoint


def generate_transaction_id_ksuid():
    from ksuid import KsuidMs

    return str(KsuidMs())


def generate_transaction_id_nanoid():
    from nanoid import generate
    from nanoid.resources import alphabet

    return generate(alphabet=alphabet[2:])


def generate_transaction_id_ulid():
    from ulid import ULID

    return str(ULID())


@dataclass
class Transaction:
    id: str = field(default_factory=generate_transaction_id_ksuid)
    request: Request = None
    response: Response = None
    created_at: datetime = field(default_factory=datetime.now)

    endpoint: ProxyEndpoint = None

    # time, tags ...

    def asdict(self):
        if self.endpoint:
            endpoint = self.endpoint.name or self.endpoint.url
        else:
            endpoint = None

        return {
            "id": self.id,
            "endpoint": endpoint,
            "request": self.request.asdict() if self.request else None,
            "response": self.response.asdict() if self.response else None,
            "createdAt": self.created_at,
        }
