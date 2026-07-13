"""Markdown renderer — the first implementation of the renderer boundary.

Pure presentation: it formats values already present in the findings and metadata. It
computes no metric and performs no analysis. Rounding and layout are the only changes.
"""

from __future__ import annotations

from math import floor, log10

from creatoros.intelligence.findings import ChannelFindings, Confidence
from creatoros.reporting.metadata import DESCRIPTIVE_DISCLAIMER, ReportMetadata

# Below this sample size the channel baseline is volatile and shifts with --limit (issue
# #47); the reader is warned so a small-sample number is not read as a channel constant.
_SMALL_SAMPLE = 10


def _num(value: float | None, digits: int = 0) -> str:
    """Format a number for display, or an em dash for a missing value."""
    if value is None:
        return "—"
    return f"{round(value):,}" if digits == 0 else f"{value:,.{digits}f}"


def _sig(value: float | None, figs: int = 3) -> str:
    """Format to a few significant figures. A baseline derived from tens of videos does
    not carry six-figure precision; showing it as ``143,747`` invents authority the
    sample cannot support (issue #47). Rounded to magnitude instead."""
    if value is None:
        return "—"
    if value == 0:
        return "0"
    decimals = figs - 1 - floor(log10(abs(value)))
    rounded = round(value, decimals)
    return f"{int(rounded):,}" if decimals <= 0 else f"{rounded:,.{decimals}f}"


def _signed(value: float | None) -> str:
    """Format a signed number (leading + or -), or an em dash for a missing value."""
    return "—" if value is None else f"{value:+,.0f}"


def _cell(text: str | None) -> str:
    """Escape a table cell so a pipe in a title cannot break the column."""
    return (text or "").replace("|", "\\|")


def _confidence_suffix(confidence: Confidence, overall_level: str) -> str:
    """A per-section confidence note, shown only when the section differs from the
    report's overall (most-conservative) level — otherwise it is stated once, in the
    header, and repeating it in every section is noise (issue #44)."""
    return (
        ""
        if confidence.level == overall_level
        else f" · confidence: {confidence.level}"
    )


class MarkdownRenderer:
    """Render canonical findings as a Markdown insight report."""

    def render(self, findings: ChannelFindings, metadata: ReportMetadata) -> str:
        title = findings.channel.title or findings.channel.channel_id
        # The report's confidence is stated once here, with its reason, then referenced
        # per-section only where a section diverges (issue #44). The overall level is
        # the most-conservative across groups — metadata already computed it.
        overall_level = metadata.confidence_summary.split(" ", 1)[0]
        overall_reason = next(
            (
                g.confidence.reason
                for g in (findings.outliers, findings.titles, findings.cadence)
                if g.confidence.level == overall_level
            ),
            "",
        )
        confidence_line = f"- **Confidence:** {metadata.confidence_summary}"
        if overall_reason:
            confidence_line += f" — {overall_reason}"
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
            confidence_line,
            "",
        ]
        lines += self._outliers(findings, overall_level)
        lines += self._titles(findings, overall_level)
        lines += self._cadence(findings, overall_level)
        return "\n".join(lines) + "\n"

    def _outliers(self, findings: ChannelFindings, overall_level: str) -> list[str]:
        o = findings.outliers
        caveat = (
            " ⚠ Small sample — this baseline is volatile and shifts with `--limit`."
            if o.sample_size < _SMALL_SAMPLE
            else ""
        )
        # The recency flag warns that a fresh video's rate is a launch spike. When no
        # video in the ranking is recent the column is uniformly "no" and pure noise
        # (issue #43), so it is shown only when it carries information.
        show_recent = any(v.is_recent for v in o.ranking)
        head = "| Video | Performance | Views/day | vs baseline |"
        rule = "| --- | --- | --- | --- |"
        if show_recent:
            head += " Recent |"
            rule += " --- |"
        lines = [
            "## Outliers",
            "",
            f"Baseline **≈{_sig(o.baseline_views_per_day)} views/day** across the "
            f"{o.sample_size} sampled videos"
            f"{_confidence_suffix(o.confidence, overall_level)}.{caveat}",
            "",
            head,
            rule,
        ]
        for v in o.ranking:
            row = (
                f"| [{_cell(v.title)}]({v.url}) | {v.performance_index:.2f}x "
                f"| {_num(v.views_per_day)} | {_signed(v.difference_views_per_day)} |"
            )
            if show_recent:
                row += f" {'yes' if v.is_recent else 'no'} |"
            lines.append(row)
        lines.append("")
        return lines

    def _titles(self, findings: ChannelFindings, overall_level: str) -> list[str]:
        t = findings.titles
        lines = [
            "## Title characteristics",
            "",
            f"Above baseline: {t.above_n} · below baseline: {t.below_n}"
            f"{_confidence_suffix(t.confidence, overall_level)}.",
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

    def _cadence(self, findings: ChannelFindings, overall_level: str) -> list[str]:
        c = findings.cadence
        return [
            "## Cadence",
            "",
            f"Uploads are **{c.regularity}** — median gap "
            f"{_num(c.median_interval_days)} days, longest {_num(c.max_interval_days)} "
            f"days, consistency (CV) {_num(c.consistency_cv, 2)}. "
            f"n={c.sample_size} dated videos"
            f"{_confidence_suffix(c.confidence, overall_level)}.",
            "",
        ]
