import re

from colorama import Fore
from honcho.process import Process


class QuietViteHonchoProcess(Process):
    """
    This is a quick hack to avoid misleading log at start of internal vite dev serversubprocess.

    """

    _muted = True
    _status = ""

    def _send_message(self, data, type="line"):
        if type == "line" and self._muted:
            if b"  VITE v" in data:
                self._status = data.decode("utf-8").strip()

            if b"Local:   http://localhost:" in data:
                url = re.search("(?P<url>https?://[^\s]+)", data.decode("utf-8")).group("url")
                super()._send_message(
                    (
                        "📈  "
                        + Fore.LIGHTBLUE_EX
                        + "Dashboard development server started."
                        + Fore.RESET
                        + (f" ({self._status})" if self._status else "")
                    ).encode(),
                )
                super()._send_message(("  ➜ Internal url: " + url).encode())
                super()._send_message(
                    "  ➜ This url is for internal use only, you should use the proxied url instead.".encode()
                )

            if b"press h + enter to show help" in data:
                self._muted = False
            return

        return super()._send_message(data, type)
