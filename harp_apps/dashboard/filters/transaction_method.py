from .base import AbstractChoicesFacet


class TransactionMethodFacet(AbstractChoicesFacet):
    name = "method"
    choices = ["GET", "POST", "PUT", "DELETE", "PATCH"]
