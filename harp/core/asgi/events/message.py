from harp.core.models.transactions import Transaction
from harp.protocols.transactions import Message

from .transaction import TransactionEvent


class MessageEvent(TransactionEvent):
    def __init__(self, transaction: Transaction, message: Message):
        super().__init__(transaction)
        self.message = message
