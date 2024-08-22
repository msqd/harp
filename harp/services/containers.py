from functools import cached_property
from inspect import signature
from typing import List, Type

from rodi import CannotResolveTypeException
from rodi import Container as BaseContainer
from rodi import OverridingServiceException, ResolutionContext, ServiceLifeStyle

from ..utils.packages import import_string
from .models import Service, ServiceCollection
from .providers import ServiceProvider
from .references import Reference


class Container(BaseContainer):
    def load(self, filename, *, bind_settings):
        collection = ServiceCollection.model_validate_yaml(filename)

        if bind_settings:
            collection.bind_settings(bind_settings)

        for service in collection:
            lifestyle = getattr(ServiceLifeStyle, (service.lifestyle or "singleton").upper())
            resolver = ServiceResolver(self, service, lifestyle)

            if resolver.base_type in self._map:
                raise OverridingServiceException(resolver.base_type, resolver)
            self._map[resolver.base_type] = resolver

            if service.name in self._exact_aliases:
                raise OverridingServiceException(service.name, resolver.base_type)
            self.set_alias(service.name, resolver.base_type)


class ServiceResolver:
    container: Container
    service: Service
    lifestyle: ServiceLifeStyle

    def __init__(self, container: Container, service: Service, lifestyle: ServiceLifeStyle):
        self.container = container
        self.service = service
        self.lifestyle = lifestyle

    def _get_resolver(self, target: str | list, context: ResolutionContext):
        if not isinstance(target, List):
            target = [target]

        for _target in target:
            if _target in context.resolved:
                return context.resolved[_target]
            if _target in self.container._exact_aliases:
                _target = self.container._exact_aliases[_target]
            elif _target in self.container._aliases:
                # XXX this looks half implemented in rodi, maybe useless
                for _alias in self.container._aliases[_target]:
                    if _alias in context.resolved:
                        _target = _alias

            reg = self.container._map.get(_target)
            if reg is None:
                continue
            resolver = reg(context)

            # add the resolver to the context, so we can find it
            # next time we need it
            context.resolved[_target] = resolver
            return resolver

        raise CannotResolveTypeException(target)

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
        if self.constructor:
            return signature(getattr(self.concrete_type, self.constructor))
        return signature(self.concrete_type)

    def __call__(self, context: ResolutionContext):
        concrete_type = self.concrete_type

        chain = context.dynamic_chain
        chain.append(concrete_type)

        args = []
        for arg in self.positionals:
            if isinstance(arg, Reference):
                args.append(self._get_resolver(arg.target, context))
            else:
                args.append(arg)

        kwargs = {}
        for _name, _value in self.defaults.items():
            if isinstance(_value, Reference):
                kwargs[_name] = _value.resolve(self._get_resolver, context)
            else:
                kwargs[_name] = _value

        for _name, _value in self.signature.parameters.items():
            if _value.annotation in self.container._map:
                kwargs.setdefault(_name, self._get_resolver(_value.annotation, context))

        for _name, _value in self.arguments.items():
            if isinstance(_value, Reference):
                kwargs[_name] = _value.resolve(self._get_resolver, context)
            else:
                kwargs[_name] = _value

        return ServiceProvider(concrete_type, self.constructor, args=args, kwargs=kwargs, lifestyle=self.lifestyle)

    def __repr__(self):
        return f"<{type(self).__name__} for {self.base_type.__name__}>"
