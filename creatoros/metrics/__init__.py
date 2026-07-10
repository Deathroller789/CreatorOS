"""Derived Metrics Engine — the layer between raw ingestion and analysis (ADR-006).

The intelligence layer asks for metrics; it never computes them, and never reads raw
fields to derive anything. Adding a metric means adding one decorated pure function to a
module in this package, then importing that module in the explicit list below — a file's
presence on disk never activates a metric on its own.

    from creatoros.metrics import compute
    derived = compute(channel, videos, now=datetime.now(UTC))
    derived.videos[video_id]["performance_index"]  # 2.7 -> 2.7x the channel baseline
"""

from __future__ import annotations

# Explicit registry: every active metric module is listed here by hand. Importing a
# module runs its @metric decorators, which self-register. A module that is NOT in this
# list stays inert — drafts, experiments, and archived metrics can live in the package
# without ever entering the registry. Explicit over automatic discovery (ADR-006:
# the repository, not a directory listing, is the source of truth for what is active).
# Import order is irrelevant — dependencies resolve at compute time, not import time.
from creatoros.metrics import channel, video  # noqa: F401
from creatoros.metrics.engine import (
    Computed,
    Metric,
    MetricError,
    compute,
    metric,
    registry,
)

__all__ = [
    "Computed",
    "Metric",
    "MetricError",
    "compute",
    "metric",
    "registry",
]
