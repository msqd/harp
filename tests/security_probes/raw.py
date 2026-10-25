"""Raw HTTP client and raw origin.

A normal HTTP client normalises malformed request lines and ambiguous framing before they reach HARP, and a normal
origin hides how the proxy rendered them. These two send and record exact bytes.
"""

import socket
import threading
import time


def send_raw(port: int, raw: bytes, wait: float = 1.2, host: str = "127.0.0.1") -> bytes:
    """Sends exact bytes to a port, returns everything read until the peer closes or ``wait`` seconds pass."""
    with socket.create_connection((host, port), 5) as sock:
        sock.sendall(raw)
        sock.settimeout(wait)
        data = b""
        deadline = time.monotonic() + wait
        try:
            while time.monotonic() < deadline:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                data += chunk
        except TimeoutError:
            pass
    return data


class Response:
    """A response read off the wire: the status line, header names and values in order, the rest as the body."""

    def __init__(self, raw: bytes):
        assert raw, "no response at all: the proxy closed the connection or never answered"
        head, _, self.body = raw.partition(b"\r\n\r\n")
        lines = head.decode("latin-1").split("\r\n")
        self.status_line = lines[0]
        self.status = int(self.status_line.split(" ", 2)[1])
        pairs = [line.split(":", 1) for line in lines[1:] if ":" in line]
        self.headers = [(name.strip().lower(), value.strip()) for name, value in pairs]

    @property
    def names(self) -> list[str]:
        return [name for name, _ in self.headers]

    def header(self, name: str) -> str | None:
        return next((value for key, value in self.headers if key == name), None)


class RawOrigin:
    """An origin that records the exact head and body bytes it received, and answers with connection-specific headers
    so the response path can be observed as well."""

    PAYLOAD = b'{"origin":"ok"}'
    RESPONSE_HEAD = (
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Type: application/json\r\n"
        b"Content-Length: " + str(len(PAYLOAD)).encode() + b"\r\n"
        b"Connection: keep-alive, X-Origin-Secret\r\n"
        b"X-Origin-Secret: leaked-via-connection-header\r\n"
        b"Keep-Alive: timeout=5, max=100\r\n"
        b"Trailer: X-Origin-Trailer\r\n"
        b"Upgrade: h2c\r\n"
        b'Proxy-Authenticate: Basic realm="origin"\r\n'
        b"X-Origin-Plain: kept\r\n"
        b"Cache-Control: no-store\r\n"
        b"\r\n"
    )

    def __init__(self):
        self.requests: list[dict] = []
        self._server = socket.create_server(("127.0.0.1", 0))
        self.port = self._server.getsockname()[1]
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}/"

    def close(self):
        self._server.close()

    def _serve(self):
        while True:
            try:
                connection, _ = self._server.accept()
            except OSError:
                return
            threading.Thread(target=self._handle, args=(connection,), daemon=True).start()

    def _handle(self, connection: socket.socket):
        with connection:
            connection.settimeout(5)
            head = b""
            try:
                while b"\r\n\r\n" not in head:
                    chunk = connection.recv(65536)
                    if not chunk:
                        return
                    head += chunk
                raw_head, _, body = head.partition(b"\r\n\r\n")
                connection.settimeout(0.35)
                try:
                    while chunk := connection.recv(65536):
                        body += chunk
                except TimeoutError:
                    pass
            except OSError:
                return
            lines = raw_head.decode("latin-1").split("\r\n")
            self.requests.append(
                {
                    "request_line": lines[0],
                    "header_names": [line.split(":", 1)[0].strip().lower() for line in lines[1:] if line],
                    "raw_head": raw_head.decode("latin-1"),
                    "body": body,
                }
            )
            try:
                connection.sendall(self.RESPONSE_HEAD + self.PAYLOAD)
            except OSError:
                pass
