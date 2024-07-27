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
                "urls": ["http://example.com"],
                "fallback_urls": ["http://fallback.example.com"],
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
                    "min_pool_size": 1,
                    "endpoints": [
                        {"failure_threshold": 3, "success_threshold": 1, "url": "http://example.com/"},
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
                        {"failure_threshold": 3, "success_threshold": 1, "url": "http://example.com/"},
                        {"failure_threshold": 3, "success_threshold": 1, "url": "http://fallback.example.com/"},
                    ],
                    "min_pool_size": 1,
                    "probe": {"type": "http", "method": "GET", "path": "/", "timeout": 5},
                },
            }
        ]
    }
