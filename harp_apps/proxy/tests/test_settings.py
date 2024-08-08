from harp.config import asdict

from ..settings import ProxySettings

short_syntax_simple_config = {
    "endpoints": [
        {
            "name": "test",
            "port": 8080,
            "url": "http://example.com",
        }
    ]
}

simple_config_with_probe = {
    "endpoints": [
        {
            "name": "test",
            "port": 8080,
            "remote": {
                "endpoints": [
                    {"url": "http://example.com"},
                    {"url": "http://fallback.example.com"},
                ],
                "probe": {
                    "method": "GET",
                    "path": "/",
                    "timeout": 5,
                },
            },
        }
    ]
}


def test_short_syntax():
    settings = ProxySettings(**short_syntax_simple_config)

    assert asdict(settings) == {
        "endpoints": [
            {
                "name": "test",
                "description": None,
                "port": 8080,
                "remote": {
                    "endpoints": [
                        {"url": "http://example.com/", "pools": ["default"]},
                    ],
                },
            }
        ]
    }


def test_default_settings():
    settings = ProxySettings()
    assert asdict(settings) == {"endpoints": []}


def test_probe_syntax():
    settings = ProxySettings(**simple_config_with_probe)
    assert asdict(settings) == {
        "endpoints": [
            {
                "description": None,
                "name": "test",
                "port": 8080,
                "remote": {
                    "endpoints": [
                        {"url": "http://example.com/", "pools": ["default"]},
                        {"url": "http://fallback.example.com/", "pools": ["default"]},
                    ],
                    "probe": {"type": "http", "method": "GET", "path": "/", "timeout": 5.0},
                },
            }
        ]
    }
