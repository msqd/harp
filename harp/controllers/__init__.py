"""
The Controllers (:mod:`harp.controllers`) package contains the routing and controller logic for the Harp framework.

You probably do not want to use this package unless you're writing an extension for Harp.

Example usage:

.. code-block:: python

    from harp.controllers import RoutingController, GetHandler


    class MyController(RoutingController):
        @GetHandler("/")
        async def index(self):
            return "Hello, world!"

Contents
--------

"""

from .default import dump_request_controller, not_found_controller
from .resolvers import DefaultControllerResolver, ProxyControllerResolver
from .routing import (
    AnyMethodHandler,
    ConnectHandler,
    DeleteHandler,
    GetHandler,
    HeadHandler,
    OptionsHandler,
    PatchHandler,
    PostHandler,
    PutHandler,
    RouteHandler,
    RouterPrefix,
    RoutingController,
    TraceHandler,
)
from .typing import IControllerResolver

__title__ = "Controllers"

__all__ = [
    "AnyMethodHandler",
    "ConnectHandler",
    "IControllerResolver",
    "DefaultControllerResolver",
    "DeleteHandler",
    "GetHandler",
    "HeadHandler",
    "OptionsHandler",
    "PatchHandler",
    "PostHandler",
    "ProxyControllerResolver",
    "PutHandler",
    "RouteHandler",
    "RouterPrefix",
    "RoutingController",
    "TraceHandler",
    "dump_request_controller",
    "not_found_controller",
]
