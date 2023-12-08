from harp.core.asgi.messages.base import AbstractASGIMessage
from harp.core.models.transactions import Transaction

from .transaction import TransactionEvent


class MessageEvent(TransactionEvent):
    def __init__(self, transaction: Transaction, message: AbstractASGIMessage):
        super().__init__(transaction)
        self.message = message
