from dataclasses import dataclass, field
from datetime import datetime

from nanoid import generate
from nanoid.resources import alphabet

from .message import Request, Response


def generate_transaction_id():
    return generate(alphabet=alphabet[2:])


@dataclass
class Transaction:
    id: str = field(default_factory=generate_transaction_id)
    request: Request = None
    response: Response = None
    created_at: datetime = field(default_factory=datetime.now)

    # time, tags ...

    def asdict(self):
        return {
            "id": self.id,
            "request": self.request.asdict() if self.request else None,
            "response": self.response.asdict() if self.response else None,
            "createdAt": self.created_at,
        }
