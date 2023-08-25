class ContentAddressable:
    def __init__(self, content: bytes):
        self._hash = None

    @property
    def id(self):
        return self.hash()

    def hash(self):
        if getattr(self, "_hash", None) is None:
            from hashlib import sha256

            self._hash = sha256(self.normalize()).hexdigest()

        return self._hash

    def normalize(self):
        raise NotImplementedError
