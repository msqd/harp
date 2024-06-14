from .base import AbstractChoicesFacet


class TransactionStatusFacet(AbstractChoicesFacet):
    name = "status"
    choices = ["2xx", "3xx", "4xx", "5xx", "ERR"]
