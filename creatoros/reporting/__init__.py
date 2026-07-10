"""Reporting — the layer that renders canonical findings into report formats.

Consumes ``ChannelFindings`` (the layer below) and turns it into a string. It performs
zero intelligence and zero metric computation; it only presents. Markdown is the first
renderer; the ``Renderer`` boundary lets others (JSON, later HTML/PDF) be added without
touching intelligence.
"""

from __future__ import annotations

from creatoros.reporting.json_renderer import JsonRenderer
from creatoros.reporting.markdown import MarkdownRenderer
from creatoros.reporting.metadata import (
    DESCRIPTIVE_DISCLAIMER,
    REPORT_FORMAT_VERSION,
    ReportMetadata,
    build_metadata,
)
from creatoros.reporting.renderer import Renderer

__all__ = [
    "DESCRIPTIVE_DISCLAIMER",
    "REPORT_FORMAT_VERSION",
    "JsonRenderer",
    "MarkdownRenderer",
    "Renderer",
    "ReportMetadata",
    "build_metadata",
]
