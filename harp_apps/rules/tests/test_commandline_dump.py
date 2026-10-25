import httpx

import harp.commandline  # noqa: F401 (harp_apps.rules.commandline cannot be imported first)
from harp_apps.http_client.events import HttpClientFilterEvent
from harp_apps.rules.commandline.utils.dump import on_remote_response_show_cache_control


async def test_show_cache_control_of_a_multi_line_header(capsys):
    event = HttpClientFilterEvent(httpx.Request("GET", "http://upstream.local/"))
    event.set_response(httpx.Response(200, headers=[("Cache-Control", "max-age=60"), ("Cache-Control", "public")]))

    await on_remote_response_show_cache_control(event)

    assert "CacheControl:" in capsys.readouterr().out
