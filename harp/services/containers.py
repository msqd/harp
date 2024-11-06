from typing import Dict, Type, Union

from rodi import Container as BaseContainer
from rodi import DynamicResolver, OverridingServiceException, ResolutionContext, ServiceLifeStyle, class_name

from .models import ServiceDefinitionCollection
from .services import Services


class Container(BaseContainer):
    """Override's rodi container with our way to load services. This is a working implementation, although it would
    need polishing. Maybe the container should be reworked entirely to avoid the rodi duplications entirely, here the
    api methods using the builtin rodi providers/resolvers are still available, and that's maybe not what we want,
    for the long term."""

    def load(self, filename, *, bind_settings):
        """
        Loads a declarative service collection from a yaml file, and bind settings for config resolution.

        :param filename: str
        :param bind_settings: dict-like
        """
        from .resolvers import ServiceResolver

        collection = ServiceDefinitionCollection.model_validate_yaml(filename)

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

    def build_provider(self) -> Services:
        """
        Builds and returns a service provider that can be used to activate and obtain
        services.

        The configuration of services is validated at this point, if any service cannot
        be instantiated due to missing dependencies, an exception is thrown inside this
        operation.

        :return: Service provider that can be used to activate and obtain services.
        """
        with ResolutionContext() as context:
            _map: Dict[Union[str, Type], Type] = {}

            for _type, resolver in self._map.items():
                if isinstance(resolver, DynamicResolver):
                    context.dynamic_chain.clear()

                if _type in context.resolved:
                    # assert _type not in context.resolved, "_map keys must be unique"
                    # check if its in the map
                    if _type in _map:
                        # NB: do not call resolver if one was already prepared for the
                        # type
                        raise OverridingServiceException(_type, resolver)
                    else:
                        resolved = context.resolved[_type]
                else:
                    # add to context so that we don't repeat operations
                    resolved = resolver(context)
                    context.resolved[_type] = resolved

                _map[_type] = resolved

                type_name = class_name(_type)
                if "." not in type_name:
                    _map[type_name] = _map[_type]

            if not self.strict:
                assert self._aliases is not None
                assert self._exact_aliases is not None

                # include aliases in the map;
                for name, _types in self._aliases.items():
                    for _type in _types:
                        break
                    _map[name] = self._get_alias_target_type(name, _map, _type)

                for name, _type in self._exact_aliases.items():
                    _map[name] = self._get_alias_target_type(name, _map, _type)

        return Services(_map)
