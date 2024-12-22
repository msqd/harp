from inspect import signature

import pytest
from rodi import ActivationScope, ServiceLifeStyle, Services

from harp.services.providers import ServiceProvider, filter_kwargs_based_on_signature


@pytest.mark.parametrize(
    "kwargs, expected",
    [
        ({"a": 1, "b": 2, "c": 3}, {"a": 1, "b": 2}),
        ({"a": 1, "b": 2, "c": 3, "d": 4}, {"a": 1, "b": 2}),
        ({"a": 1, "b": 2}, {"a": 1, "b": 2}),
        ({"a": 1, "b": 2, "c": 3, "d": 4, "e": 5}, {"a": 1, "b": 2}),
        ({}, {}),
        ({"c": 3, "d": 4, "e": 5}, {}),
    ],
)
def test_filter_kwargs_based_on_signature(kwargs, expected):
    def func(a, b):
        pass

    sig = signature(func)
    assert filter_kwargs_based_on_signature(kwargs, sig) == expected


class TestServiceProvider:
    @pytest.fixture(autouse=True)
    def setup(self):
        class DummyService:
            def __init__(self, a, b):
                self.a = a
                self.b = b

            def constructor(self):
                self.a = 1
                self.b = 2

        self.args = []
        self.kwargs = {}
        self.constructor = DummyService
        self.lifestyle = ServiceLifeStyle.SINGLETON
        self.provider = ServiceProvider(self.constructor, args=self.args, kwargs=self.kwargs, lifestyle=self.lifestyle)

    def test_constructor_property(self):
        assert self.provider.constructor == self.constructor

        provider_with_constructor = ServiceProvider(
            self.constructor, _constructor="constructor", args=self.args, kwargs=self.kwargs, lifestyle=self.lifestyle
        )
        assert provider_with_constructor.constructor == self.constructor.constructor

    def test_signature_property(self):
        assert self.provider.signature == signature(self.constructor)

        provider_with_constructor = ServiceProvider(
            self.constructor, _constructor="constructor", args=self.args, kwargs=self.kwargs, lifestyle=self.lifestyle
        )
        assert provider_with_constructor.signature == signature(self.constructor.constructor)

    def test_call_method_missing_arguments(self):
        services = Services({"dummy_service": self.provider})
        activation_scope = ActivationScope(services)

        # without any args or kwargs specified this should throw an error
        with pytest.raises(TypeError):
            self.provider(activation_scope)

    def test_call_method_with_kwargs(self):
        provider = ServiceProvider(self.constructor, args=[], kwargs={"a": 1, "b": 2}, lifestyle=self.lifestyle)
        services = Services({"dummy_service": provider})
        activation_scope = ActivationScope(services)

        instance = provider(activation_scope)
        assert instance.a == 1
        assert instance.b == 2

    def test_call_method_with_args(self):
        provider = ServiceProvider(self.constructor, args=[1, 2], kwargs={}, lifestyle=self.lifestyle)
        services = Services({"dummy_service": provider})
        activation_scope = ActivationScope(services)

        instance = provider(activation_scope)
        assert instance.a == 1
        assert instance.b == 2

    def test_call_method_with_args_and_kwargs(self):
        provider = ServiceProvider(self.constructor, args=[1], kwargs={"b": 2}, lifestyle=self.lifestyle)
        services = Services({"dummy_service": provider})
        activation_scope = ActivationScope(services)

        instance = provider(activation_scope)
        assert instance.a == 1
        assert instance.b == 2

    def test_call_method_with_overlapping_args_and_kwargs(self):
        provider = ServiceProvider(self.constructor, args=[1], kwargs={"a": 1, "b": 2}, lifestyle=self.lifestyle)
        services = Services({"dummy_service": provider})
        activation_scope = ActivationScope(services)

        with pytest.raises(TypeError):
            provider(activation_scope)

    def test_bind_arguments(self):
        provider = ServiceProvider(self.constructor, args=[], kwargs={"a": 1}, lifestyle=self.lifestyle)
        services = Services({"dummy_service": provider})
        activation_scope = ActivationScope(services)

        with pytest.raises(TypeError):
            provider(activation_scope)

        # now binding the missing argument
        provider.bind(b=2)

        instance = provider(activation_scope)
        assert instance.a == 1
        assert instance.b == 2
