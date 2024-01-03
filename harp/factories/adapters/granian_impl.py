import threading
from collections.abc import Collection
from functools import partial
from typing import List

from granian import Granian as OriginalServerImpl
from granian.constants import HTTPModes, Interfaces, Loops, ThreadModes
from granian.log import LogLevels
from granian.server import Worker

from harp.factories.proxy import Bind

"""
Notes:

For this to work, we need to be able to pass the asgi callable to a fork, with multiprocessing passing data using a
ForkingPickler.

Which means that we need to be able to construct the asgi callable based on this picklable stuff.

So we need to clearly separate the factory process in a few steps (was in the plans anyway):
- configuration step: purely declarative, no real code execution/configuration/instanciation/surlepondavinion
  this step can easily be serializable/unserializable.

- build step: build everything, gogogo.
  maybe this step needs two sub steps (ok lets say 3 in total) for bind/mount then run. Or maybe not.

Once this is done, the adapters should get the configured but not built factory, and hypercorn adapter can just build
and run while granian adapter can serialize the factory, and pass it to the fork which will rebuild the callables.

This is a bit more complicated than I thought, but it should work. Maybe a little discussion about some refactorings in
granian should be opened, but first let's make a proof of concept.

"""


class Granian(type("CleanedUpServerImpl", (OriginalServerImpl,), {})):
    def __init__(self, target, binds: Collection[Bind]):
        self.target = target
        self.binds = list(binds)

        # compat
        self.bind_addr = self.binds[0].host
        if self.bind_addr == "[::]":
            self.bind_addr = "0.0.0.0"
        self.bind_port = self.binds[0].port
        self.interface = Interfaces.ASGI
        self.workers = 1
        self.threads = 1
        self.pthreads = 1
        self.threading_mode = ThreadModes.workers
        self.loop = Loops.auto
        self.loop_opt = False
        self.http = HTTPModes.auto
        self.websockets = True
        self.backlog = 1024
        self.http1_buffer_size = 65535
        self.url_path_prefix = None

        self.log_enabled = True
        self.log_level = (LogLevels.info,)
        self.log_config = None

        self.ssl_ctx = (False, None, None)
        self._shd = None
        self._sfd = None
        self.procs: List[Worker] = []
        self.main_loop_interrupt = threading.Event()
        self.interrupt_signal = False
        self.interrupt_child = None

    def serve(self):
        return self._serve(self._spawn_asgi_worker, partial(load, self.target))


def load(x):
    return x
