from pydantic import BaseModel


class GlobalSettings(dict[str, BaseModel | list]):
    """
    Placeholder type for injecting global settings as a dictionary. Usually, you'd prefer to use the "local" settings
    of your application, but sometimes you need to access the global settings. For example, the dashboard uses it to
    display all the running instance settings in a system tab.
    """
