from ..utils.dependencies import parse_dependencies


def test_parse_dependencies():
    assert parse_dependencies(
        [
            "aiofiles==23.2.1",
            "aiohttp==3.9.1",
            "aiosignal==1.3.1",
            "aiosqlite==0.19.0",
            "anyio==4.2.0",
            "ASGIMiddlewareStaticFile==0.6.1",
            "asgiref==3.7.2",
            "asyncpg==0.29.0",
            "attrs==23.2.0",
            "certifi==2023.11.17",
            "click==8.1.7",
            "dataclasses-json==0.6.3",
            "dataclasses-jsonschema==2.16.0",
            "-e /opt/harp/src/vendors/config",
            "frozenlist==1.4.1",
            "greenlet==3.0.3",
            "h11==0.14.0",
            "h2==4.1.0",
            "-e /opt/harp/src",
            "hpack==4.0.0",
            "http-router==4.0.0",
            "httpcore==1.0.2",
            "httpx==0.26.0",
            "Hypercorn==0.16.0",
            "hyperframe==6.0.1",
            "idna==3.6",
            "jsonschema==4.20.0",
            "jsonschema-specifications==2023.12.1",
            "markdown-it-py==3.0.0",
            "marshmallow==3.20.1",
            "mdurl==0.1.2",
            "multidict==6.0.4",
            "mypy-extensions==1.0.0",
            "orjson==3.9.10",
            "packaging==23.2",
            "passlib==1.7.4",
            "priority==2.0.0",
            "psycopg2-binary==2.9.9",
            "Pygments==2.17.2",
            "python-baseconv==1.2.2",
            "python-dateutil==2.8.2",
            "python-dotenv==1.0.0",
            "PyYAML==6.0.1",
            "referencing==0.32.0",
            "rich==13.7.0",
            "rich-click==1.7.2",
            "-e /opt/harp/src/vendors/rodi",
            "rpds-py==0.16.2",
            "six==1.16.0",
            "sniffio==1.3.0",
            "SQLAlchemy==2.0.24",
            "SQLAlchemy-Utils==0.41.1",
            "structlog==23.3.0",
            "svix-ksuid==0.6.2",
            "typing-inspect==0.9.0",
            "typing_extensions==4.9.0",
            "-e /opt/harp/src/vendors/whistle",
            "wsproto==1.2.0",
            "yarl==1.9.4",
        ]
    ) == {
        "ASGIMiddlewareStaticFile": "0.6.1",
        "Hypercorn": "0.16.0",
        "PyYAML": "6.0.1",
        "Pygments": "2.17.2",
        "SQLAlchemy": "2.0.24",
        "SQLAlchemy-Utils": "0.41.1",
        "aiofiles": "23.2.1",
        "aiohttp": "3.9.1",
        "aiosignal": "1.3.1",
        "aiosqlite": "0.19.0",
        "anyio": "4.2.0",
        "asgiref": "3.7.2",
        "asyncpg": "0.29.0",
        "attrs": "23.2.0",
        "certifi": "2023.11.17",
        "click": "8.1.7",
        "config": "-e /opt/harp/src/vendors/config",
        "dataclasses-json": "0.6.3",
        "dataclasses-jsonschema": "2.16.0",
        "frozenlist": "1.4.1",
        "greenlet": "3.0.3",
        "h11": "0.14.0",
        "h2": "4.1.0",
        "hpack": "4.0.0",
        "http-router": "4.0.0",
        "httpcore": "1.0.2",
        "httpx": "0.26.0",
        "hyperframe": "6.0.1",
        "idna": "3.6",
        "jsonschema": "4.20.0",
        "jsonschema-specifications": "2023.12.1",
        "markdown-it-py": "3.0.0",
        "marshmallow": "3.20.1",
        "mdurl": "0.1.2",
        "multidict": "6.0.4",
        "mypy-extensions": "1.0.0",
        "orjson": "3.9.10",
        "packaging": "23.2",
        "passlib": "1.7.4",
        "priority": "2.0.0",
        "psycopg2-binary": "2.9.9",
        "python-baseconv": "1.2.2",
        "python-dateutil": "2.8.2",
        "python-dotenv": "1.0.0",
        "referencing": "0.32.0",
        "rich": "13.7.0",
        "rich-click": "1.7.2",
        "rodi": "-e /opt/harp/src/vendors/rodi",
        "rpds-py": "0.16.2",
        "six": "1.16.0",
        "sniffio": "1.3.0",
        "src": "-e /opt/harp/src",
        "structlog": "23.3.0",
        "svix-ksuid": "0.6.2",
        "typing-inspect": "0.9.0",
        "typing_extensions": "4.9.0",
        "whistle": "-e /opt/harp/src/vendors/whistle",
        "wsproto": "1.2.0",
        "yarl": "1.9.4",
    }
