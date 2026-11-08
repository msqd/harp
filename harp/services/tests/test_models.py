from harp.services.models import ServiceDefinition


def test_override_with_takes_every_set_field_of_the_other():
    base = ServiceDefinition(name="a", description="d", lifestyle="singleton", base="b", type="t", constructor="c")
    other = ServiceDefinition(
        name="a",
        description="d2",
        lifestyle="transient",
        base="b2",
        type="t2",
        constructor="c2",
        arguments={"x": 1},
        defaults={"y": 2},
        positionals=(3,),
    )
    assert base.override_with(other) == other


def test_override_with_keeps_own_fields_the_other_leaves_unset():
    base = ServiceDefinition(name="a", description="d", lifestyle="singleton", type="t", arguments={"x": 1})
    result = base.override_with(ServiceDefinition(name="a", type="t2"))
    assert (result.description, result.lifestyle, result.type, result.arguments) == ("d", "singleton", "t2", {"x": 1})


def test_override_with_drops_the_override_condition():
    base = ServiceDefinition(name="a", override="cond")
    assert base.override_with(ServiceDefinition(name="a")).override is None
