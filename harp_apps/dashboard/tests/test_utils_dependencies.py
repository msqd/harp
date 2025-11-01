from ..utils.dependencies import (
    get_python_dependencies,
    parse_dependencies,
)


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
        "config": "editable",
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
        "rodi": "editable",
        "rpds-py": "0.16.2",
        "six": "1.16.0",
        "sniffio": "1.3.0",
        "src": "editable",
        "structlog": "23.3.0",
        "svix-ksuid": "0.6.2",
        "typing-inspect": "0.9.0",
        "typing_extensions": "4.9.0",
        "whistle": "editable",
        "wsproto": "1.2.0",
        "yarl": "1.9.4",
    }


def test_parse_dependencies_handles_unusual_formats():
    """Test that parse_dependencies handles unusual package formats like direct file references.

    This was a bug found after release 0.6 where pip freeze output included packages
    installed from direct file references (e.g., 'package @ file:///path').
    While importlib.metadata doesn't generate this format, parse_dependencies should
    remain robust to handle it for backward compatibility.
    """
    deps_with_unusual_formats = [
        "aiofiles==24.1.0",
        "aiohttp==3.9.5",
        "harp-proxy @ file:///harp_proxy-0.6.0a4-py3-none-any.whl#sha256=f28d1d01c38d7647eccf1a58d550f58c5db97509f95369993a684603ebb30e9e",
        "Hypercorn==0.17.3",
        "redis==5.0.7",
        "whistle==2.0.0b1",
    ]

    result = parse_dependencies(deps_with_unusual_formats)

    # The unusual format should be parsed with "unknown" version
    assert (
        result[
            "harp-proxy @ file:///harp_proxy-0.6.0a4-py3-none-any.whl#sha256=f28d1d01c38d7647eccf1a58d550f58c5db97509f95369993a684603ebb30e9e"
        ]
        == "unknown"
    )

    # Normal packages should parse correctly
    assert result["aiofiles"] == "24.1.0"
    assert result["aiohttp"] == "3.9.5"
    assert result["Hypercorn"] == "0.17.3"
    assert result["redis"] == "5.0.7"
    assert result["whistle"] == "2.0.0b1"


async def test_get_python_dependencies():
    """Test that get_python_dependencies returns installed packages using importlib.metadata."""
    deps = await get_python_dependencies()
    # Should return list of strings in format "package==version"
    assert isinstance(deps, list)
    assert len(deps) > 0
    # Check format of at least one package
    assert any("==" in dep for dep in deps)
