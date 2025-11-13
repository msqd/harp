import time
from http.client import HTTPConnection
from subprocess import DEVNULL, Popen

import pytest


@pytest.fixture(scope="session")
def process():
    """Start HARP server in background and wait for it to be ready."""
    process = Popen(["make", "start"], stdout=DEVNULL, stderr=DEVNULL)
    retries = 10
    while retries > 0:
        try:
            conn = HTTPConnection("localhost:4080")
            conn.request("HEAD", "/")
            response = conn.getresponse()
            if response is not None:
                yield process
                break
        except (ConnectionRefusedError, OSError):
            time.sleep(1)
            retries -= 1
        finally:
            try:
                conn.close()
            except:
                pass

    if not retries:
        raise RuntimeError("Failed to start http server")
    else:
        process.terminate()
        process.wait()
