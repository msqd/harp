from rodi import Container as BaseContainer
from rodi import OverridingServiceException, ServiceLifeStyle, Services

from .models import ServiceCollection


class Container(BaseContainer):
    def load(self, filename, *, bind_settings):
        from .resolvers import ServiceResolver

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

    def build_provider(self) -> Services:
        provider = super().build_provider()
        return provider
