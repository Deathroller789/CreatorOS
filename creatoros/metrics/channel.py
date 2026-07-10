"""Channel-scope derived metrics. A channel metric sees a video metric as a series."""

from __future__ import annotations

import statistics

from creatoros.metrics.engine import metric


@metric(scope="channel", unit="views/day", depends_on=("views_per_day",))
def median_views_per_day(views_per_day: list[float]) -> float | None:
    """The channel's baseline. Median, not mean: one viral video must not move it."""
    if not views_per_day:
        return None
    return statistics.median(views_per_day)
