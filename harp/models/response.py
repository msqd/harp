from dataclasses import dataclass

from .message import DeprecatedOldTransactionMessage


@dataclass(kw_only=True)
class DeprecatedOldTransactionResponse(DeprecatedOldTransactionMessage):
    status_code: int

    def normalize(self):
        return b"\n".join(
            (
                b"HTTP/1.1 " + str(self.status_code).encode(),
                b"",
                super().normalize(),
            )
        )

    def asdict(self, *, with_details=False):
        return super().asdict(with_details=with_details) | {
            "statusCode": self.status_code,
        }
