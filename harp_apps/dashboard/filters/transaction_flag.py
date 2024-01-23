from .base import AbstractFacet


class TransactionFlagFacet(AbstractFacet):
    name = "flag"
    choices = {"favorite"}
