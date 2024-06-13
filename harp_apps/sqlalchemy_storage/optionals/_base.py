from abc import ABC, abstractmethod


class BaseOptional(ABC):
    @abstractmethod
    async def is_supported(self) -> bool:
        """Is this optional supported in the current environment?"""
        raise NotImplementedError()

    @abstractmethod
    async def install(self):
        """Install this optional feature in the database."""
        raise NotImplementedError()

    @abstractmethod
    async def uninstall(self):
        """Uninstall this optional feature from the database."""
        raise NotImplementedError()
