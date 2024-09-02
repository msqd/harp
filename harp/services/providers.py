from functools import cached_property
from inspect import BoundArguments, Parameter, Signature, signature

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

    def _resolve_arguments(self, scope: ActivationScope, parent_type) -> BoundArguments:
        """Create a bound argument object after resolving all the arguments (aka transforming "provider" type values
        into their actual alive counterpart."""
        try:
            sig = signature(self.constructor)
        except ValueError:
            # for objects that cannot give their signatures, we try to forge one. Of course, this will be limited, but
            # we need to somehow support it because of cython obejcts, for example.
            sig = Signature(
                [
                    *(Parameter(str(i), Parameter.POSITIONAL_ONLY) for i in range(len(self._args))),
                    *(Parameter(k, Parameter.KEYWORD_ONLY) for k in self._kwargs),
                ]
            )

        def _resolve(arg):
            if isinstance(arg, PROVIDER_TYPES):
                return arg(scope, parent_type)
            return arg

        try:
            return sig.bind(
                *(_resolve(v) for v in self._args),
                **{k: _resolve(v) for k, v in self._kwargs.items()},
            )
        except TypeError as exc:
            raise TypeError(f"Error resolving arguments for {self._type.__name__}: {exc}") from exc

    def _create_instance(self, scope: ActivationScope, parent_type):
        """Create an instance of the service each time it is called."""
        arguments = self._resolve_arguments(scope, parent_type=parent_type)
        return self.constructor(*arguments.args, **arguments.kwargs)

    def __call__(self, scope: ActivationScope, parent_type=None):
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
