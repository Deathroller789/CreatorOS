"""The renderer boundary: (findings, metadata) -> a formatted report string.

Markdown is the first renderer; JSON follows. Adding a renderer requires no change to
the intelligence layer or to the findings contract — that is the point of the boundary.
A renderer is presentation only: it computes no metrics and performs no analysis.
"""

from __future__ import annotations

from typing import Protocol

from creatoros.intelligence.findings import ChannelFindings
from creatoros.reporting.metadata import ReportMetadata


class Renderer(Protocol):
    """Turns canonical findings and their metadata into a formatted report string."""

    def render(self, findings: ChannelFindings, metadata: ReportMetadata) -> str: ...
