import datetime


class AbstractASGIMessage:
    kind: str
    serialized_summary: str
    serialized_headers: str
    serialized_body: bytes
    created_at: datetime.datetime
