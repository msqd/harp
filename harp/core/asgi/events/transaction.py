from whistle import Event

from harp.core.models.transactions import Transaction


class TransactionEvent(Event):
    def __init__(self, transaction: Transaction):
        self.transaction = transaction
