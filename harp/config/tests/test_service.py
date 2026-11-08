from harp.config import Service


def test_validation_leaves_the_source_mapping_untouched():
    source = {"type": "foo.Bar", "retries": 3, "arguments": {"timeout": 10}}

    first = Service.model_validate(source)
    second = Service.model_validate(source)

    assert source == {"type": "foo.Bar", "retries": 3, "arguments": {"timeout": 10}}
    assert first.arguments == second.arguments == {"timeout": 10, "retries": 3}
