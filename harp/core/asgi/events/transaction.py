from harp.core.models.transactions import Transaction

from .base import BaseEvent


class TransactionEvent(BaseEvent):
    def __init__(self, transaction: Transaction):
        self.transaction = transaction
