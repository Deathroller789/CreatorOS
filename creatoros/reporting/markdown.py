"""Markdown renderer — the first implementation of the renderer boundary.

Pure presentation: it formats values already present in the findings and metadata. It
computes no metric and performs no analysis. Rounding and layout are the only changes.
"""

from __future__ import annotations

from creatoros.intelligence.findings import ChannelFindings
from creatoros.reporting.metadata import DESCRIPTIVE_DISCLAIMER, ReportMetadata


def _num(value: float | None, digits: int = 0) -> str:
    """Format a number for display, or an em dash for a missing value."""
    if value is None:
        return "—"
    return f"{round(value):,}" if digits == 0 else f"{value:,.{digits}f}"


def _signed(value: float | None) -> str:
    """Format a signed number (leading + or -), or an em dash for a missing value."""
    return "—" if value is None else f"{value:+,.0f}"


def _cell(text: str | None) -> str:
    """Escape a table cell so a pipe in a title cannot break the column."""
    return (text or "").replace("|", "\\|")


class MarkdownRenderer:
    """Render canonical findings as a Markdown insight report."""

    def render(self, findings: ChannelFindings, metadata: ReportMetadata) -> str:
        title = findings.channel.title or findings.channel.channel_id
        lines: list[str] = [
            f"# Channel Intelligence — {title}",
            "",
            f"_{DESCRIPTIVE_DISCLAIMER}_",
            "",
            "## Report",
            "",
            f"- **CreatorOS version:** {metadata.creatoros_version}",
            f"- **Metric engine version:** {metadata.metric_engine_version}",
            f"- **Report format:** v{metadata.report_format_version}",
            f"- **Generated:** {metadata.generated_at}",
            f"- **Channel:** {title} (`{metadata.channel_id}`)",
            f"- **Sample size:** {metadata.sample_size} videos",
            f"- **Confidence:** {metadata.confidence_summary}",
            "",
        ]
        lines += self._outliers(findings)
        lines += self._titles(findings)
        lines += self._cadence(findings)
        return "\n".join(lines) + "\n"

    def _outliers(self, findings: ChannelFindings) -> list[str]:
        o = findings.outliers
        lines = [
            "## Outliers",
            "",
            f"Baseline **{_num(o.baseline_views_per_day)} views/day** · "
            f"n={o.sample_size} · confidence: {o.confidence.level} (evidence quality).",
            "",
            "| Video | Performance | Views/day | vs baseline | Recent |",
            "| --- | --- | --- | --- | --- |",
        ]
        for v in o.ranking:
            lines.append(
                f"| [{_cell(v.title)}]({v.url}) | {v.performance_index:.2f}x "
                f"| {_num(v.views_per_day)} | {_signed(v.difference_views_per_day)} "
                f"| {'yes' if v.is_recent else 'no'} |"
            )
        lines.append("")
        return lines

    def _titles(self, findings: ChannelFindings) -> list[str]:
        t = findings.titles
        lines = [
            "## Title characteristics",
            "",
            f"Above baseline: {t.above_n} · below baseline: {t.below_n} · "
            f"confidence: {t.confidence.level} (evidence quality).",
            "",
        ]
        if not t.features:
            return [*lines, "_Not enough videos in both groups to compare titles._", ""]
        lines += [
            "| Metric | Above mean | Below mean | Difference | Effect size (d) | n |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for c in t.features:
            effect = "—" if c.effect_size is None else f"{c.effect_size:+.2f}"
            lines.append(
                f"| {c.metric} ({c.unit}) | {c.above_mean:.1f} | {c.below_mean:.1f} "
                f"| {c.difference:+.1f} | {effect} | {c.above_n}/{c.below_n} |"
            )
        lines += [
            "",
            "_Correlation is not causation; several features are compared, so treat "
            "any single difference cautiously._",
            "",
        ]
        return lines

    def _cadence(self, findings: ChannelFindings) -> list[str]:
        c = findings.cadence
        return [
            "## Cadence",
            "",
            f"Uploads are **{c.regularity}** — median gap "
            f"{_num(c.median_interval_days)} days, longest {_num(c.max_interval_days)} "
            f"days, consistency (CV) {_num(c.consistency_cv, 2)}. "
            f"n={c.sample_size} dated videos · confidence: {c.confidence.level} "
            "(evidence quality).",
            "",
        ]
