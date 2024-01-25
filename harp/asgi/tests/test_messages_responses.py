from unittest.mock import AsyncMock, Mock

import pytest

from harp.asgi.messages import ASGIResponse


async def test_headers_readonly_after_start():
    send = AsyncMock()
    response = ASGIResponse(Mock(), send)
    response.headers["content-type"] = "text/plain"
    await response.start()
    with pytest.raises(TypeError):
        response.headers["content-type"] = "text/html"
