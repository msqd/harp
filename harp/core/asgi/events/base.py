from whistle import Event


class BaseEvent(Event):
    dispatcher = None
    name = None
