from functools import cached_property
from inspect import BoundArguments, Parameter, Signature, signature
from typing import Optional, Type, TypeVar, Union

from rodi import (
    ActivationScope,
    ArgsTypeProvider,
    FactoryTypeProvider,
    InstanceProvider,
    ScopedArgsTypeProvider,
    ScopedFactoryTypeProvider,
    ScopedTypeProvider,
    ServiceLifeStyle,
    SingletonFactoryTypeProvider,
    SingletonTypeProvider,
    TypeProvider,
)

T = TypeVar("T")


def filter_kwargs_based_on_signature(kwargs, signature: Signature):
    """Filter out kwargs that are not in the signature or that are not allowed as keyword arguments."""
    return {
        k: v
        for k, v in kwargs.items()
        if k in signature.parameters
        and signature.parameters[k].kind in (Parameter.KEYWORD_ONLY, Parameter.POSITIONAL_OR_KEYWORD)
    }


class ServiceProvider:
    def __init__(self, _type, _constructor=None, *, args, kwargs, lifestyle):
        self._type = _type
        self._constructor = _constructor
        self._args = args
        self._kwargs = kwargs
        self._lifestyle = lifestyle

        if self._lifestyle == ServiceLifeStyle.SINGLETON:
            self._instance = None

    @cached_property
    def constructor(self):
        return self._type if not self._constructor else getattr(self._type, self._constructor)

    @property
    def signature(self):
        try:
            sig = signature(self.constructor)
        except ValueError:
            # for objects that cannot give their signatures, we try to forge one. Of course, this will be limited, but
            # we need to somehow support it because of cython objects, for example.
            sig = Signature(
                [
                    *(Parameter(str(i), Parameter.POSITIONAL_ONLY) for i in range(len(self._args))),
                    *(Parameter(k, Parameter.KEYWORD_ONLY) for k in self._kwargs),
                ]
            )
        return sig

    def _resolve_arguments(self, scope: ActivationScope, parent_type) -> BoundArguments:
        """Create a bound argument object after resolving all the arguments (aka transforming "provider" type values
        into their actual alive counterpart."""

        def _resolve(arg):
            if isinstance(arg, PROVIDER_TYPES):
                return arg(scope, parent_type)
            return arg

        resolved_args = (_resolve(v) for v in self._args)
        resolved_kwargs = {k: _resolve(v) for k, v in {**self._kwargs}.items()}
        try:
            return self.signature.bind(*resolved_args, **resolved_kwargs)
        except TypeError as exc:
            raise TypeError(f"Error resolving arguments for {self._type.__name__}: {exc}") from exc

    def _create_instance(self, scope: ActivationScope, parent_type):
        """Create an instance of the service each time it is called."""
        arguments = self._resolve_arguments(scope, parent_type=parent_type)
        return self.constructor(
            *arguments.args,
            **arguments.kwargs,
        )

    def __call__(self, scope: ActivationScope, parent_type: Optional[Union[Type[T], str]] = None):
        """Resolves this provider into a service instance, creating it if necessary (will depend on service's life
        style)."""
        parent_type = parent_type or self._type

        # singleton lifestyle will get instanciated only once (by provider, two different providers for the same service
        # would create 2 instances-.
        if self._lifestyle == ServiceLifeStyle.SINGLETON:
            if not self._instance:
                self._instance = self._create_instance(scope, parent_type)
            return self._instance

        # scoped lifestyle will get instanciated only once per scope (for example, a web request)
        if self._lifestyle == ServiceLifeStyle.SCOPED:
            if self._type not in scope.scoped_services:
                scope.scoped_services[self._type] = self._create_instance(scope, parent_type)
            return scope.scoped_services[self._type]

        # default / transient lifestyle will get instanciated each time it is called
        return self._create_instance(scope, parent_type)

    def bind(self, **kwargs):
        """Add additional arguments to the service provider.
        We check that arguments are in the signature of the service type before adding them.
        """
        sig = self.signature
        filtered_kwargs = filter_kwargs_based_on_signature(kwargs, sig)
        self._kwargs.update(filtered_kwargs)


PROVIDER_TYPES = (
    ServiceProvider,
    InstanceProvider,
    TypeProvider,
    ScopedTypeProvider,
    ArgsTypeProvider,
    FactoryTypeProvider,
    SingletonFactoryTypeProvider,
    ScopedFactoryTypeProvider,
    ScopedArgsTypeProvider,
    SingletonTypeProvider,
)
