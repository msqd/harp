from harp.core.models.transactions import Transaction
from whistle import Event


class TransactionEvent(Event):
    def __init__(self, transaction: Transaction):
        self.transaction = transaction
