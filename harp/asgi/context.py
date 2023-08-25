from functools import cached_property

from harp import get_logger

logger = get_logger(__name__)


class AsgiContext:
    def __init__(self, scope, receive, send):
        self._scope = scope
        self._receive = receive
        self._send = send

    def __enter__(self):
        logger.debug(f"◁ ENTER {self.type}", **self._scope)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return

    @cached_property
    def scope(self):
        return self._scope

    @cached_property
    def type(self):
        return self._scope["type"]

    @cached_property
    def server_port(self):
        return self._scope["server"][1]

    def send(self, ctx):
        logger.debug(f"▷ SEND {ctx['type']}", **ctx)
        return self._send(ctx)

    async def send_all(self, *ctxs):
        for ctx in ctxs:
            await self.send(ctx)

    async def receive(self):
        retval = await self._receive()
        logger.debug(f"◁ RECV {self.type}", **retval)
        return retval

    async def _extract_request_content(self):
        """
        todo we should not remove the buffering ability, httpx allows us to stream the request body but for that we need
        some kind of stream processor that yields and store the chunks.

        :param ctx:
        :return:
        """
        messages = []
        more_body = True
        while more_body:
            message = await self.receive()
            more_body = message.get("more_body", False)
            if len(message["body"]):
                messages.append(message["body"])
        return b"".join(messages) if len(messages) else None
