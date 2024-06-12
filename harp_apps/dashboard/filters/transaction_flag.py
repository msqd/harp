from .base import AbstractChoicesFacet


class TransactionFlagFacet(AbstractChoicesFacet):
    name = "flag"
    choices = {"favorite"}
