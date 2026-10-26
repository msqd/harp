from harp.models.transactions import CacheOutcome

from .base import AbstractChoicesFacet


class TransactionCacheFacet(AbstractChoicesFacet):
    name = "cache"
    choices = [outcome.value for outcome in CacheOutcome]
