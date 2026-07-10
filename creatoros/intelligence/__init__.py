"""Channel Intelligence — the Analysis layer over the metrics engine.

Consumes derived metrics, answers the V1 questions (outliers, title characteristics,
cadence), and returns canonical findings. It knows nothing of any output format; a
renderer in the reporting layer turns findings into a report. See
docs/modules/002-channel-intelligence.md.
"""

from __future__ import annotations

from creatoros.intelligence.analyze import IntelligenceError, analyze_channel
from creatoros.intelligence.findings import (
    CadenceFindings,
    ChannelFindings,
    ChannelRef,
    Confidence,
    OutlierFindings,
    TitleFeatureComparison,
    TitleFindings,
    VideoOutlier,
)

__all__ = [
    "CadenceFindings",
    "ChannelFindings",
    "ChannelRef",
    "Confidence",
    "IntelligenceError",
    "OutlierFindings",
    "TitleFeatureComparison",
    "TitleFindings",
    "VideoOutlier",
    "analyze_channel",
]
