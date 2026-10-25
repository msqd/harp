"""A stand-in for an application that performs critical actions, so it declares ``audit`` in its dependencies."""

from harp.config import Application

application = Application(dependencies=["audit"])
