"""User docs run `harp-proxy server`; `harp-proxy start` is the development launcher, documented for contributors only."""

from pathlib import Path

DOCS = Path(__file__).parent.parent / "docs"
DEVELOPMENT_DOCS = (DOCS / "contribute", DOCS / "apps" / "dashboard" / "development")


def test_user_docs_do_not_run_the_development_launcher():
    offenders = [
        str(path.relative_to(DOCS))
        for path in DOCS.rglob("*.rst")
        if "harp-proxy start" in path.read_text() and not any(d in path.parents for d in DEVELOPMENT_DOCS)
    ]
    assert offenders == []
