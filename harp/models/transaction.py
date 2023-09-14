from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .base import Entity
from .proxy_endpoint import ProxyEndpoint
from .request import TransactionRequest
from .response import TransactionResponse
from .utils import generate_transaction_id_ksuid


@dataclass
class Transaction(Entity):
    id: str = field(default_factory=generate_transaction_id_ksuid)
    request: TransactionRequest = None
    response: TransactionResponse = None

    created_at: datetime = field(default_factory=datetime.now)
    elapsed: timedelta = None

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
            "elapsed": self.elapsed.total_seconds() if self.elapsed else None,
        }

    def children(self):
        yield from filter(None, (self.request, self.response))
