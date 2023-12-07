from dataclasses import dataclass

from harp.core.models.base import Entity
from harp.models.base import ContentAddressable

interesting_headers_order = [
    b"content",
    b"accept",
    b"cache",
]


def header_key(header):
    k, v = header[0].lower(), header[1].lower()
    sk = k.split(b"-")
    try:
        i = interesting_headers_order.index(sk[0])
    except ValueError:
        i = len(interesting_headers_order)
    return i, k, v


def get_headers_as_dict(headers):
    return {
        k.decode("utf-8").title(): v.decode("utf-8")
        for k, v in sorted(
            headers,
            key=header_key,
        )
    }


@dataclass
class DeprecatedOldTransactionMessage(ContentAddressable, Entity):
    headers: tuple
    content: bytes | None

    def normalize(self):
        return b"\n".join(
            (
                *(k + b": " + v for k, v in self.headers),
                b"",
                self.content or b"",
            )
        )

    def asdict(self, *, with_details=False):
        return {
            "id": self.id,
            **(
                {
                    "content": self.content.decode() if self.content else None,
                    "headers": get_headers_as_dict(self.headers),
                }
                if with_details
                else {}
            ),
        }
