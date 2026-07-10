"""Derived Metrics Engine — the layer between raw ingestion and analysis (ADR-006).

The intelligence layer asks for metrics; it never computes them, and never reads raw
fields to derive anything. Adding a metric means adding one decorated pure function to a
module in this package — nothing else changes, and nothing else needs to know.

    from creatoros.metrics import compute
    derived = compute(channel, videos, now=datetime.now(UTC))
    derived.videos[video_id]["performance_index"]  # 2.7 -> 2.7x the channel baseline
"""

from __future__ import annotations

import importlib
import pkgutil

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


def _discover() -> None:
    """Import every metric module so that importing this package fills the registry."""
    for module in pkgutil.iter_modules(__path__):
        if module.name != "engine":
            importlib.import_module(f"{__name__}.{module.name}")


_discover()
