"""JSON renderer — findings as a deterministic, machine-readable document.

Same ``Renderer`` contract as Markdown, same inputs, no change to intelligence. It is
the structured counterpart to the Markdown report: identical information, different form
(a later PR makes this the canonical exchange format). Presentation only — it serializes
values already present in the findings and metadata; it computes nothing.

Named ``json_renderer`` (not ``json``) so ``import json`` here unambiguously means the
standard library, never this module.
"""

from __future__ import annotations

import json
from dataclasses import asdict

from creatoros.intelligence.findings import ChannelFindings
from creatoros.reporting.metadata import DESCRIPTIVE_DISCLAIMER, ReportMetadata


class JsonRenderer:
    """Render canonical findings and their metadata as deterministic JSON."""

    def render(self, findings: ChannelFindings, metadata: ReportMetadata) -> str:
        document = {
            "notice": DESCRIPTIVE_DISCLAIMER,
            "metadata": asdict(metadata),
            "findings": asdict(findings),
        }
        # Fixed field order (from the dataclasses) + a trailing newline = byte-stable
        # output for the same findings. No sort_keys: the declared order is meaningful.
        return json.dumps(document, indent=2, ensure_ascii=False) + "\n"
