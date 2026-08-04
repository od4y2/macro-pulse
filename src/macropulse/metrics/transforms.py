def percent_change(current: float, previous: float) -> float:
    if previous == 0:
        raise ValueError("previous value must be non-zero")
    return 100.0 * (current / previous - 1.0)

def weighted_coverage(available_weights: list[float], all_weights: list[float]) -> float:
    total = sum(all_weights)
    if total <= 0:
        raise ValueError("total weight must be positive")
    return sum(available_weights) / total
