from .base import NonExhaustiveFacet


class TransactionFlagFacet(NonExhaustiveFacet):
    name = "flag"
    choices = {"favorite"}
