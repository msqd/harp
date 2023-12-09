from typing import Protocol


class IStorage(Protocol):
    def find_transactions(self, *, with_messages=False):
        ...

    def get_blob(self, blob_id):
        ...
