from .base import AbstractFacet


class TransactionStatusFacet(AbstractFacet):
    name = "status"
    choices = {"2xx", "3xx", "4xx", "5xx"}
