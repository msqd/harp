import time
from http.client import HTTPConnection
from subprocess import PIPE, Popen

import pytest


@pytest.fixture(scope="session")
def process():
    process = Popen(["make", "start"], stdout=PIPE)
    retries = 5
    while retries > 0:
        conn = HTTPConnection("localhost:4080")
        try:
            conn.request("HEAD", "/")
            response = conn.getresponse()
            if response is not None:
                yield process
                break
        except ConnectionRefusedError:
            time.sleep(1)
            retries -= 1

    if not retries:
        raise RuntimeError("Failed to start http server")
    else:
        process.terminate()
        process.wait()
