from dataclasses import dataclass


@dataclass
class Request:
    method: str
    url: str
    headers: tuple
    body: bytes | None

    def asdict(self):
        return {
            "method": self.method,
            "url": self.url,
            "headers": self.headers,
            "body": self.body,
        }


@dataclass
class Response:
    status_code: int
    headers: tuple
    body: bytes

    def asdict(self):
        return {
            "statusCode": self.status_code,
            "headers": self.headers,
            "body": self.body,
        }
