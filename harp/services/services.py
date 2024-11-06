from typing import Any, Optional, Type, TypeVar, Union, cast

from rodi import ActivationScope, CannotResolveTypeException
from rodi import Services as BaseServices

T = TypeVar("T")


class Services(BaseServices):
    """
    A service container that provides services to the application.

    This class extends the
    `Rodi Services <https://rodi.readthedocs.io/en/latest/services.html>`_
    class, adding support for resolving services based on their type annotations.

    """

    def get(
        self,
        desired_type: Union[Type[T], str],
        scope: Optional[ActivationScope] = None,
        *,
        default: Optional[Any] = ...,
        **kwargs: Any,
    ) -> T:
        """
        Gets a service of the desired type, returning an activated instance.

        :param desired_type: desired service type.
        :param context: optional context, used to handle scoped services.
        :return: an instance of the desired type
        """
        if scope is None:
            scope = ActivationScope(self)

        resolver = self._map.get(desired_type)
        scoped_service = scope.scoped_services.get(desired_type) if scope else None

        if not resolver and not scoped_service:
            if default is not ...:
                return cast(T, default)
            raise CannotResolveTypeException(desired_type)

        return cast(T, scoped_service or resolver(scope, desired_type, **kwargs))
