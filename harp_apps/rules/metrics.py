from prometheus_client import Counter

RULES_FAILURES = Counter(
    "rules_failures_count",
    "Count of rule scripts that failed, by endpoint, rule level and reason (error or timeout).",
    ["endpoint", "rule", "reason"],
)
