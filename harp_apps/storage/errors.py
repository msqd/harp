class StorageTimeLimitExceeded(Exception):
    """A storage query ran longer than the time limit its caller set, and was stopped."""

    def __init__(self, time_limit: float):
        self.time_limit = time_limit
        super().__init__(f"Storage query exceeded its time limit of {time_limit:g}s.")
