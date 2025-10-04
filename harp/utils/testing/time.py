import os


def get_adjusted_timeout(base_timeout: float = 10.0) -> float:
    """Adjust timeout based on system load.

    Args:
        base_timeout: Base timeout in seconds.

    Returns:
        Adjusted timeout value.
    """
    try:
        # Get system load average (1, 5, 15 minutes)
        load_avg = os.getloadavg()[0]
        cpu_count = os.cpu_count() or 1

        # Calculate load factor (load per CPU)
        load_factor = load_avg / cpu_count

        # Adjust timeout based on load
        if load_factor < 1.5:
            return base_timeout
        elif load_factor < 3.0:
            return base_timeout * 1.5
        else:
            return min(base_timeout * 2.0, 30.0)
    except AttributeError:
        # Windows doesn't have getloadavg
        return base_timeout * 1.5
