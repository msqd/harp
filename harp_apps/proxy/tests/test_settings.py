from harp.config.asdict import asdict

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
                    {"url": "http://fallback.example.com", "pools": ["fallback"]},
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
    settings = ProxySettings.from_dict(short_syntax_simple_config)

    assert asdict(settings) == {
        "endpoints": [
            {
                "name": "test",
                "port": 8080,
                "remote": {
                    "endpoints": [
                        {"url": "http://example.com/"},
                    ]
                },
            }
        ]
    }


def test_default_settings():
    settings = ProxySettings()
    assert asdict(settings) == {}


def test_probe_syntax():
    settings = ProxySettings.from_dict(simple_config_with_probe)
    assert asdict(settings) == {
        "endpoints": [
            {
                "name": "test",
                "port": 8080,
                "remote": {
                    "endpoints": [
                        {"url": "http://example.com/"},
                        {"pools": ["fallback"], "url": "http://fallback.example.com/"},
                    ],
                    "probe": {"timeout": 5.0},
                },
            }
        ]
    }
