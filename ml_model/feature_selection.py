"""Adaptive feature selection used in comparison with the fixed feature baseline."""

from sklearn.feature_selection import SelectPercentile, chi2


def make_adaptive_selector(percentile: int = 20) -> SelectPercentile:
    """Select the highest scoring percentile, adapting to available feature count."""
    if not 1 <= percentile <= 100:
        raise ValueError("percentile must be between 1 and 100")
    return SelectPercentile(score_func=chi2, percentile=percentile)
