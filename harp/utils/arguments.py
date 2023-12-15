class Arguments:
    __slots__ = ["_args", "_kwargs"]

    def __init__(self, *args, **kwargs):
        self._args = args
        self._kwargs = kwargs

    @property
    def args(self):
        return self._args

    @property
    def kwargs(self):
        return self._kwargs
