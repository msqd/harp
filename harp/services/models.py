from typing import Annotated, Any, Iterable, Literal, Mapping, Optional, Self, Sequence, Tuple, Union

from pydantic import BaseModel, ConfigDict, Discriminator, Tag

from harp.utils.config import yaml

from .references import LazyServiceReference, LazySettingReference

StringOrRef = str | LazySettingReference | LazyServiceReference
ExtendedStringOrRef = StringOrRef | bool


def _resolve(value: Optional[ExtendedStringOrRef | Iterable[ExtendedStringOrRef]], settings: Any):
    if value is None:
        return None
    if isinstance(value, (bool, str, LazyServiceReference)):
        return value
    if isinstance(value, Mapping):
        return {k: _resolve(v, settings) for k, v in value.items()}
    if isinstance(value, LazySettingReference):
        return value.resolve(settings)
    for x in value:
        x = _resolve(x, settings)
        if x is not None:
            return x
    return None


class ServiceDefinition(BaseModel):
    """
    Describes a service that our container is able to register. Services within a collection can override each other,
    if explicitely stated. This is useful for conditional service change (for example, based on a configuration value).

    """

    model_config = ConfigDict(extra="forbid")

    #: service name (todo: constraints ?)
    name: str

    #: service description, for documentation and readbility purposes
    description: Optional[str] = None

    #: service lifestyle
    lifestyle: Optional[Literal["singleton", "transient", "scoped"]] = None

    #: condition to be met for the service to register or override another one
    override: Optional[str] = None

    #: base type for service, aka the interface we are implementing, if different from type
    base: Optional[StringOrRef | Sequence[StringOrRef]] = None

    #: service type, aka the implementation we are using, if different from base
    type: Optional[StringOrRef | Sequence[StringOrRef]] = None

    #: constructor name, if not default one
    constructor: Optional[StringOrRef | Sequence[StringOrRef]] = None

    #: default named arguments for the service constructor. Can be both positionnal or keyword based, but the
    # parameter choice is always based on parameter name, by key.
    defaults: Optional[Mapping[str, Any] | Sequence[Mapping[str, Any] | LazySettingReference]] = None

    #: named arguments for the service constructor. Mapped after the annotation parsing, so it can override default
    # attributions from type annotations.
    arguments: Optional[Mapping[str, Any] | Sequence[Mapping[str, Any] | LazySettingReference]] = None

    #: positionnal arguments for the service constructor.
    positionals: Optional[Tuple[Any, ...]] = None

    def override_with(self, other: Self) -> Self:
        if self.name != other.name:
            raise ValueError(f"Service name mismatch: {self.name} != {other.name}")

        # todo scope override limitation, as it is most probably a mistake.

        return type(self)(
            name=self.name,
            description=(other.description if other.description is not None else self.description),
            lifestyle=(other.lifestyle if other.lifestyle is not None else self.lifestyle),
            base=other.base if other.base is not None else self.base,
            type=other.type if other.type is not None else self.type,
            constructor=(other.constructor if other.constructor is not None else self.constructor),
            arguments=(other.arguments if other.arguments is not None else self.arguments),
            defaults=other.defaults if other.defaults is not None else self.defaults,
            positionals=(other.positionals if other.positionals is not None else self.positionals),
        )

    def bind_settings(self, settings: Any):
        for k in ("base", "type", "constructor"):
            setattr(self, k, _resolve(getattr(self, k), settings))

        self.defaults = _resolve(self.defaults, settings)
        self.arguments = _resolve(self.arguments, settings)


def _discriminator(obj):
    if "services" in obj:
        if "condition" in obj:
            return "conditional_collection"
        return "collection"
    return "service"


class BaseServiceDefinitionCollection(BaseModel):
    """
    Base class for coherent sequences of services. The traverse() method can be used to get a flat iterator over all
    the service definitions in the collection and its children, ordered.

    """

    services: Sequence[
        Annotated[
            Union[
                Annotated["ServiceDefinition", Tag("service")],
                Annotated["BaseServiceDefinitionCollection", Tag("collection")],
                Annotated["ConditionalServiceDefinitionCollection", Tag("conditional_collection")],
            ],
            Discriminator(_discriminator),
        ]
    ]

    def traverse(self) -> Iterable[ServiceDefinition]:
        for service_or_collection in iter(self.services):
            if isinstance(service_or_collection, ServiceDefinition):
                yield service_or_collection
            else:
                yield from service_or_collection.traverse()

    def bind_settings(self, settings: Any):
        for service in self.services:
            service.bind_settings(settings)


class ConditionalServiceDefinitionCollection(BaseServiceDefinitionCollection):
    """
    A collection of services that are only registered if a condition is met. This is useful for conditional service
    registration, for example based on a configuration value.

    """

    condition: Optional[
        Union[
            str | bool | LazySettingReference,
            Sequence[str | bool | LazySettingReference],
        ]
    ] = None

    def bind_settings(self, settings: Any):
        if self.condition:
            self.condition = _resolve(self.condition, settings)
        super().bind_settings(settings)

    def traverse(self) -> Iterable[ServiceDefinition]:
        if self.condition:
            yield from super().traverse()


class ServiceDefinitionCollection(BaseServiceDefinitionCollection):
    """
    Final class for a service collection. Iterate on it to get a flattened (one level) and merged (services with same
    name that allows overrides are merged together) list of services.

    """

    def __iter__(self) -> Iterable[ServiceDefinition]:
        _map = {}
        for service in self.traverse():
            if service.name in _map:
                if not service.override:
                    raise ValueError(
                        f"Service with name {service.name} is already defined, but no override flag is set."
                    )
                _map[service.name] = _map[service.name].override_with(service)
                continue

            if service.override:
                raise ValueError(f"Service with name {service.name} is not defined, but override flag is set.")
            _map[service.name] = service

        return iter(_map.values())

    @classmethod
    def model_validate_yaml(cls, filename):
        return cls.model_validate(yaml.load(filename))
