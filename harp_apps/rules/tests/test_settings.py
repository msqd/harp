import os

from yaml import load

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

import harp
from harp_apps.rules.settings import RulesSettings

with open(os.path.join(harp.ROOT_DIR, "docs/apps/rules/examples/rules.yml")) as f:
    example_rules = load(f, Loader=Loader).get("rules")


def test_idempotence():
    settings = RulesSettings(**example_rules)
    normalized_sources = settings._asdict()
    assert normalized_sources == {
        "*": {
            "*": {
                "on_request": "request.headers['X-Forwarded-For'] = 'Joe'",
            }
        },
        "httpbin-*": {
            "GET /*": {
                "on_remote_response": "response.headers['Cache-Control'] = 'max-age=3600'",
            }
        },
    }

    settings = RulesSettings(**normalized_sources)
    assert normalized_sources == settings._asdict()


def test_apply():
    settings = RulesSettings(
        **{
            "*": {
                "*": {
                    "*": ["foo = 42"],
                }
            }
        }
    )

    context = {}
    for script in settings.ruleset.match("api1", "GET /foo", "on_request"):
        script(context)
    assert context == {"foo": 42}
