from functools import cached_property
from inspect import signature
from typing import List, Type

from rodi import CannotResolveTypeException, ResolutionContext, ServiceLifeStyle

from harp.utils.packages import import_string

from .containers import Container
from .models import ServiceDefinition
from .providers import ServiceProvider
from .references import LazyServiceReference


class ServiceResolver:
    container: Container
    service: ServiceDefinition
    lifestyle: ServiceLifeStyle

    def __init__(
        self,
        container: Container,
        service: ServiceDefinition,
        lifestyle: ServiceLifeStyle,
    ):
        self.container = container
        self.service = service
        self.lifestyle = lifestyle

    def _get_resolver(self, desired_type: str | list, context: ResolutionContext):
        # we use a list to support fallbacks
        if not isinstance(desired_type, List):
            desired_type = [desired_type]

        for _type in desired_type:
            # first, resolve aliases
            if _type in self.container._exact_aliases:
                _type = self.container._exact_aliases[_type]
            elif _type in self.container._aliases:
                # XXX this looks half implemented in rodi, maybe useless
                for _alias in self.container._aliases[_type]:
                    if _alias in context.resolved:
                        _type = _alias

            # if we already have a resolver, we're done.
            if _type in context.resolved:
                return context.resolved[_type]

            reg = self.container._map.get(_type)
            if reg is None:
                continue
            resolver = reg(context)

            # add the resolver to the context, so we can find it next time we need it
            context.resolved[_type] = resolver
            return resolver

        raise CannotResolveTypeException(desired_type)

    @cached_property
    def base_type(self):
        return import_string(self.service.base) if self.service.base else self.concrete_type

    @cached_property
    def concrete_type(self) -> Type:
        _type = self.service.type or self.service.base
        if isinstance(_type, str):
            return import_string(_type)
        for candidate in _type:
            if candidate is not None and isinstance(candidate, str):
                return import_string(candidate)
        raise ValueError(f"Could not resolve concrete type for service {self.service.name}.")

    @cached_property
    def positionals(self):
        return self.service.positionals if self.service.positionals is not None else ()

    @cached_property
    def arguments(self):
        return self.service.arguments if self.service.arguments is not None else {}

    @cached_property
    def defaults(self):
        return self.service.defaults if self.service.defaults is not None else {}

    @cached_property
    def constructor(self):
        return self.service.constructor

    @cached_property
    def signature(self):
        # try to build the signature object, or return None if it is not possible. Cython objects for example does not
        # have signatures (see https://cython.readthedocs.io/en/latest/src/userguide/limitations.html#inspect-support)
        if self.constructor:
            try:
                return signature(getattr(self.concrete_type, self.constructor))
            except ValueError:
                return None
        try:
            return signature(self.concrete_type)
        except ValueError:
            return None

    def __call__(self, context: ResolutionContext):
        concrete_type = self.concrete_type

        chain = context.dynamic_chain
        chain.append(concrete_type)

        args = []
        for arg in self.positionals:
            if isinstance(arg, LazyServiceReference):
                args.append(self._get_resolver(arg.target, context))
            else:
                args.append(arg)

        kwargs = {}
        for _name, _value in self.defaults.items():
            if isinstance(_value, LazyServiceReference):
                kwargs[_name] = _value.resolve(self._get_resolver, context)
            else:
                kwargs[_name] = _value

        if self.signature:
            for _name, _value in self.signature.parameters.items():
                if _value.annotation in self.container._map:
                    kwargs.setdefault(_name, self._get_resolver(_value.annotation, context))

        for _name, _value in self.arguments.items():
            if isinstance(_value, LazyServiceReference):
                kwargs[_name] = _value.resolve(self._get_resolver, context)
            else:
                kwargs[_name] = _value

        return ServiceProvider(
            concrete_type,
            self.constructor,
            args=args,
            kwargs=kwargs,
            lifestyle=self.lifestyle,
        )

    def __repr__(self):
        return f"<{type(self).__name__} for {self.base_type.__name__}>"
