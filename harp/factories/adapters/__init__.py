import os

from harp import get_logger
from harp.factories.adapters.base import AbstractServerAdapter, AdaptableFactory

logger = get_logger(__name__)


def get_server_adapter(target: AdaptableFactory) -> AbstractServerAdapter:
    """
    Returns a server adapter for the target based on the HARP_SERVER environment variable.

    :param target: a proxy factory (or anything adaptable to a server)
    :return: a server adapter, that can be served
    """

    impl = os.environ.get("HARP_SERVER", "hypercorn")

    logger.info(f"Using server adapter: {impl}")

    if impl == "hypercorn":
        from harp.factories.adapters.hypercorn_adapter import HypercornServerAdapter

        return HypercornServerAdapter(target)
    elif impl == "granian":
        from harp.factories.adapters.granian_adapter import GranianServerAdapter

        return GranianServerAdapter(target)

    raise NotImplementedError(f"Unknown server adapter: {impl}")
