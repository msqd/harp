from .base import NonExhaustiveFacet


class TransactionFlagFacet(NonExhaustiveFacet):
    name = "flag"
    choices = ["favorite"]
    fallback_name = "no flag"
