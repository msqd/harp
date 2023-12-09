from harp.core.event_dispatcher import BaseEvent
from harp.core.models.transactions import Transaction


class TransactionEvent(BaseEvent):
    def __init__(self, transaction: Transaction):
        self.transaction = transaction
