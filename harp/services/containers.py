from rodi import Container as BaseContainer
from rodi import OverridingServiceException, ServiceLifeStyle

from .models import ServiceDefinitionCollection


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
