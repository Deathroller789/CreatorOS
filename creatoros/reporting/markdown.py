"""Markdown renderer — the first implementation of the renderer boundary.

Pure presentation: it formats values already present in the findings and metadata. It
computes no metric and performs no analysis. Rounding, wording, and layout are the only
changes it makes.

The report is written for a creator, not for the codebase: sections are named for what a
creator would call them, metrics are shown by their plain-language label, and support is
communicated as *strength* rather than as a standardised effect size. The JSON renderer
remains the lossless, technical form — Cohen's d and registry metric names live there.
Families are iterated generically, so a new family renders with no change here.
"""

from __future__ import annotations

from math import floor, log10

from creatoros.intelligence.findings import (
    ChannelFindings,
    Confidence,
    CorpusGroup,
    FeatureGroup,
    OutlierFindings,
)
from creatoros.reporting.metadata import DESCRIPTIVE_DISCLAIMER, ReportMetadata

# Below this many videos in the baseline basis, the baseline is volatile and shifts with
# `--limit` (issue #48); the reader is warned so a small-sample number is not read as a
# channel constant.
_SMALL_SAMPLE = 10

# Units whose values are proportions and read best as percentages.
_PERCENT_UNITS = ("0/1", "ratio")


def _num(value: float | None, digits: int = 0) -> str:
    """Format a number for display, or an em dash for a missing value."""
    if value is None:
        return "—"
    return f"{round(value):,}" if digits == 0 else f"{value:,.{digits}f}"


def _sig(value: float | None, figs: int = 3) -> str:
    """Format to a few significant figures. A baseline derived from tens of videos does
    not carry six-figure precision; showing it as ``143,747`` invents authority the
    sample cannot support (issue #48). Rounded to magnitude instead."""
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


def _measure(value: float, unit: str, signed: bool = False) -> str:
    """Format a metric value the way its unit reads best to a creator.

    Proportions become percentages ("27%" not "0.27"), rates keep one decimal, pace is
    whole words per minute. The unit itself is never printed in the cell — it belongs in
    the metric's label, where a creator will actually read it.
    """
    sign = "+" if signed and value >= 0 else ""
    if unit in _PERCENT_UNITS:
        return f"{sign}{value * 100:.0f}%"
    if unit == "words/minute":
        return f"{sign}{value:,.0f}"
    if unit in ("characters", "words"):
        return f"{sign}{value:,.1f}"
    return f"{sign}{value:,.1f}"


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
        # per-section only where a section diverges (#44). The overall level is the
        # most-conservative across the primary groups; metadata already computed it.
        overall_level = metadata.confidence_summary.split(" ", 1)[0]
        overall_reason = next(
            (
                g.confidence.reason
                for g in (
                    findings.outliers,
                    findings.cadence,
                    *findings.feature_groups,
                )
                if g.confidence.level == overall_level
            ),
            "",
        )
        # The metadata phrases this as "low (evidence quality)" for machine consumers;
        # under a heading that already says "Evidence quality", repeating reads badly.
        confidence_line = f"- **Evidence quality:** {overall_level}"
        if overall_reason:
            confidence_line += f" — {overall_reason}"
        lines: list[str] = [
            f"# Channel Intelligence — {title}",
            "",
            f"_{DESCRIPTIVE_DISCLAIMER}_",
            "",
            "## About this report",
            "",
            f"- **Channel:** {title} (`{metadata.channel_id}`)",
            f"- **Videos analysed:** {metadata.sample_size}",
            confidence_line,
            f"- **Generated:** {metadata.generated_at}",
            f"- **CreatorOS version:** {metadata.creatoros_version}"
            f" · engine {metadata.metric_engine_version}"
            f" · report format v{metadata.report_format_version}",
            "",
        ]
        lines += self._performance(findings.outliers, overall_level)
        for group in findings.feature_groups:
            lines += self._feature_group(group, overall_level)
        if findings.feature_groups:
            # Stated once for the whole report rather than under every table (Part G).
            lines += [
                "_These are differences that accompany performance, not causes of it."
                " Several patterns are compared, so treat any single one cautiously._",
                "",
            ]
        for group in findings.corpus_groups:
            lines += self._corpus_group(group, overall_level)
        lines += self._cadence(findings, overall_level)
        return "\n".join(lines) + "\n"

    def _performance(self, o: OutlierFindings, overall_level: str) -> list[str]:
        caveat = (
            " ⚠ Small sample — this baseline is volatile and shifts with `--limit`."
            if o.baseline_basis_n < _SMALL_SAMPLE
            else ""
        )
        basis = f"the middle of {o.baseline_basis_n} settled videos"
        if o.baseline_iqr_low is not None and o.baseline_iqr_high is not None:
            basis += (
                f"; most sit between {_sig(o.baseline_iqr_low)} and "
                f"{_sig(o.baseline_iqr_high)} views/day"
            )
        if o.baseline_excluded_recent:
            basis += f"; {o.baseline_excluded_recent} too new to count yet"
        # The recency flag warns that a fresh video's rate is a launch spike. When no
        # video in the ranking is recent the column is uniformly "no" and pure noise
        # (issue #43), so it is shown only when it carries information.
        show_recent = any(v.is_recent for v in o.ranking)
        head = "| Video | vs typical | Views/day | Difference |"
        rule = "| --- | --- | --- | --- |"
        if show_recent:
            head += " Still new |"
            rule += " --- |"
        lines = [
            "## Performance",
            "",
            f"A typical video earns about "
            f"**{_sig(o.baseline_views_per_day)} views/day** "
            f"— {basis}{_confidence_suffix(o.confidence, overall_level)}.{caveat}",
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

    def _feature_group(self, g: FeatureGroup, overall_level: str) -> list[str]:
        lines = [
            f"## {g.label}",
            "",
            f"Comparing {g.grouping}{_confidence_suffix(g.confidence, overall_level)}.",
            "",
            "| Pattern | Stronger videos | Weaker videos | Difference | Strength |",
            "| --- | --- | --- | --- | --- |",
        ]
        for c in g.features:
            lines.append(
                f"| {_cell(c.label)} | {_measure(c.above_mean, c.unit)} "
                f"| {_measure(c.below_mean, c.unit)} "
                f"| {_measure(c.difference, c.unit, signed=True)} | {c.strength} |"
            )
        lines.append("")
        return lines

    def _corpus_group(self, g: CorpusGroup, overall_level: str) -> list[str]:
        intro = (
            f"Found across {g.basis_n} videos"
            f"{_confidence_suffix(g.confidence, overall_level)}."
        )
        if g.coverage_note:
            intro += f" _{g.coverage_note}._"
        lines = [f"## {g.label}", "", intro, ""]
        show_split = any(p.above_count is not None for p in g.phrases)
        if show_split:
            lines += [
                "| Phrase | In videos | Stronger | Weaker | Strength |",
                "| --- | --- | --- | --- | --- |",
            ]
            for p in g.phrases:
                lines.append(
                    f"| {_cell(p.text)} | {p.document_count} of {g.basis_n} "
                    f"| {p.above_count} of {g.above_n} "
                    f"| {p.below_count} of {g.below_n} | {p.strength} |"
                )
        else:
            lines += ["| Phrase | In videos | Strength |", "| --- | --- | --- |"]
            for p in g.phrases:
                lines.append(
                    f"| {_cell(p.text)} | {p.document_count} of {g.basis_n} "
                    f"| {p.strength} |"
                )
        lines.append("")
        return lines

    def _cadence(self, findings: ChannelFindings, overall_level: str) -> list[str]:
        c = findings.cadence
        return [
            "## Publishing rhythm",
            "",
            f"Uploads are **{c.regularity}** — typically every "
            f"{_num(c.median_interval_days)} days, with the longest gap "
            f"{_num(c.max_interval_days)} days. Based on {c.sample_size} dated videos"
            f"{_confidence_suffix(c.confidence, overall_level)}.",
            "",
        ]
