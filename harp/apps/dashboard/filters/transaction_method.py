from .base import AbstractFacet


class TransactionMethodFacet(AbstractFacet):
    name = "method"
    choices = {"GET", "POST", "PUT", "DELETE", "PATCH"}
