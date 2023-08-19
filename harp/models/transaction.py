from dataclasses import dataclass, field
from datetime import datetime

from ksuid import KsuidMs
from nanoid import generate
from nanoid.resources import alphabet

from .message import Request, Response
from .proxy_endpoint import ProxyEndpoint


def generate_transaction_id():
    return str(KsuidMs())
    return generate(alphabet=alphabet[2:])


@dataclass
class Transaction:
    id: str = field(default_factory=generate_transaction_id)
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
