from harp_apps.rules.models.compilers import BaseRuleSetCompiler
from harp_apps.rules.models.patterns import Pattern
from harp_apps.rules.models.rulesets import BaseRuleSet, RuleSet
from harp_apps.rules.models.scripts import Script


def test_simple():
    rs = RuleSet()
    rs.add({"*": {"*": {"*": 'print("Hello, World!")'}}})
    assert rs._asdict() == {"*": {"*": {"*": "print('Hello, World!')"}}}


def test_compile():
    compiler = BaseRuleSetCompiler()
    compiled = compiler.compile({"foo": "print('Hello, World!')"})

    assert compiled == {
        Pattern("foo"): [
            Script("print('Hello, World!')"),
        ]
    }


def test_multilevel():
    levels = ("first", "second")
    compiler = BaseRuleSetCompiler(levels=levels)

    # compile a first ruleset
    compiled = compiler.compile({"foo": {"bar": "print('Hello, World!')"}})
    assert compiled == {
        Pattern("foo"): {
            Pattern("bar"): [
                Script("print('Hello, World!')"),
            ]
        }
    }

    # compile a second ruleset, merging it with the first
    compiled = compiler.compile({"foo": {"bar": "print('Eat at Joe\\'s.')"}}, target=compiled)
    assert compiled == {
        Pattern("foo"): {
            Pattern("bar"): [
                Script("print('Hello, World!')"),
                Script("print('Eat at Joe\\'s.')"),
            ]
        }
    }

    ruleset = BaseRuleSet(compiled, levels=compiler.levels)
    assert list(ruleset.match("toto", "tata")) == []
    assert list(ruleset.match("foo", "bar")) == [
        Script("print('Hello, World!')"),
        Script("print('Eat at Joe\\'s.')"),
    ]


def test_repr():
    levels = ("first", "second")
    compiler = BaseRuleSetCompiler(levels=levels)
    ruleset = BaseRuleSet(compiler.compile({"foo": {"bar": "print('Hello, World!')"}}))
    assert repr(ruleset) == 'BaseRuleSet({"foo":{"bar":"..."}})'
