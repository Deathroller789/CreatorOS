"""The derived-metrics engine: a registry plus a dependency-ordered evaluator.

Raw -> Derived -> Analysis (ADR-006). Metric functions are pure: they are handed plain
values and return a value. They never open a database, never read a file, and never call
another metric themselves. The engine owns discovery, dependency ordering, and null
propagation, so that adding a metric is additive rather than invasive.

A metric declares its ``scope`` (is it a property of one video, or of the whole channel
sample?), its ``unit``, and the names it ``depends_on``. Each dependency name is either
another registered metric or a raw field on the record being computed. The engine
resolves the difference; the metric author does not care.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any, Literal

Scope = Literal["video", "channel"]


class MetricError(Exception):
    """Raised when metrics are declared or resolved incorrectly."""


@dataclass(frozen=True, slots=True)
class Metric:
    """A single derived metric: a pure function plus the metadata to schedule it."""

    name: str
    scope: Scope
    unit: str
    depends_on: tuple[str, ...]
    fn: Callable[..., Any]
    # Optional grouping so a consumer can request a family of metrics ("title", ...)
    # by kind instead of naming each one — the roadmap-#19 category, kept additive. A
    # metric with no category simply belongs to no family. Defaulted last so existing
    # positional Metric(...) construction is unaffected.
    category: str | None = None


_REGISTRY: dict[str, Metric] = {}


def metric(
    *,
    scope: Scope,
    unit: str,
    depends_on: Iterable[str] = (),
    category: str | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Register the decorated pure function as a derived metric.

    The function's parameter names must match ``depends_on`` exactly, in order — that is
    the whole contract, and it is checked at import time so a typo fails loudly.
    ``category`` optionally groups the metric into a family (e.g. ``"title"``).
    """
    deps = tuple(depends_on)

    def decorate(fn: Callable[..., Any]) -> Callable[..., Any]:
        name = fn.__name__
        if scope not in ("video", "channel"):
            raise MetricError(f"metric {name!r}: scope must be 'video' or 'channel'")
        if not unit:
            raise MetricError(f"metric {name!r}: unit is required")
        if name in _REGISTRY:
            raise MetricError(f"metric {name!r} is already registered")
        params = tuple(inspect.signature(fn).parameters)
        if params != deps:
            raise MetricError(
                f"metric {name!r}: parameters {params} must match "
                f"depends_on {deps} exactly, in order"
            )
        _REGISTRY[name] = Metric(name, scope, unit, deps, fn, category=category)
        return fn

    return decorate


def registry(category: str | None = None) -> dict[str, Metric]:
    """Return registered metrics keyed by name.

    With ``category`` set, return only the metrics in that family — so a consumer can
    ask for "every title metric" without hard-coding their names (ADR-006: adding a
    metric to a family must not require editing the code that consumes the family).
    """
    if category is None:
        return dict(_REGISTRY)
    return {name: m for name, m in _REGISTRY.items() if m.category == category}


@dataclass(frozen=True, slots=True)
class Computed:
    """Derived values: channel-scope by name, video-scope by video id then name."""

    channel: dict[str, Any]
    videos: dict[str, dict[str, Any]]


def _select(metrics: dict[str, Metric], only: Iterable[str] | None) -> set[str]:
    """Return ``only`` closed over its transitive metric dependencies."""
    if only is None:
        return set(metrics)
    wanted: set[str] = set()
    queue = list(only)
    while queue:
        name = queue.pop()
        if name in wanted:
            continue
        if name not in metrics:
            raise MetricError(f"unknown metric {name!r}")
        wanted.add(name)
        queue.extend(d for d in metrics[name].depends_on if d in metrics)
    return wanted


def _order(wanted: set[str], metrics: dict[str, Metric]) -> list[Metric]:
    """Topologically sort ``wanted`` so every metric follows its dependencies."""
    order: list[Metric] = []
    done: set[str] = set()
    visiting: set[str] = set()

    def visit(name: str, stack: tuple[str, ...]) -> None:
        if name in done:
            return
        if name in visiting:
            raise MetricError(
                "circular metric dependency: " + " -> ".join((*stack, name))
            )
        visiting.add(name)
        for dep in metrics[name].depends_on:
            if dep in metrics:
                visit(dep, (*stack, name))
        visiting.discard(name)
        done.add(name)
        order.append(metrics[name])

    for name in sorted(wanted):
        visit(name, ())
    return order


def _video_kwargs(
    m: Metric,
    metrics: dict[str, Metric],
    raw: dict[str, Any],
    derived: dict[str, Any],
    channel_values: dict[str, Any],
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    for dep in m.depends_on:
        declared = metrics.get(dep)
        if declared is None:
            if dep not in raw:
                raise MetricError(
                    f"metric {m.name!r} depends on {dep!r}, which is neither a "
                    f"registered metric nor a raw field on the video"
                )
            kwargs[dep] = raw[dep]
        elif declared.scope == "channel":
            kwargs[dep] = channel_values[dep]
        else:
            kwargs[dep] = derived[dep]
    return kwargs


def _channel_kwargs(
    m: Metric,
    metrics: dict[str, Metric],
    raw: dict[str, Any],
    videos: list[dict],
    video_values: dict[str, dict[str, Any]],
    channel_values: dict[str, Any],
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    for dep in m.depends_on:
        declared = metrics.get(dep)
        if declared is None:
            if dep not in raw:
                raise MetricError(
                    f"metric {m.name!r} depends on {dep!r}, which is neither a "
                    f"registered metric nor a raw field on the channel"
                )
            kwargs[dep] = raw[dep]
        elif declared.scope == "video":
            # A channel metric aggregating a video metric sees the whole sample as a
            # series. Videos where the metric is undefined drop out of the series.
            series = [video_values[v["video_id"]][dep] for v in videos]
            kwargs[dep] = [value for value in series if value is not None]
        else:
            kwargs[dep] = channel_values[dep]
    return kwargs


def compute(
    channel: dict,
    videos: list[dict],
    now: Any,
    only: Iterable[str] | None = None,
    metrics: dict[str, Metric] | None = None,
) -> Computed:
    """Compute derived metrics for a channel and its video sample.

    ``now`` is injected as a raw field on every record, which is what keeps
    age-normalized metrics pure and testable. Pass ``only`` to request a subset; its
    dependencies are pulled in automatically. A metric whose scalar dependencies are not
    all available evaluates to ``None`` rather than raising — missing data is normal,
    and it propagates.
    """
    metrics = registry() if metrics is None else dict(metrics)
    for v in videos:
        if not v.get("video_id"):
            raise MetricError("every video needs a 'video_id'")

    channel_raw = {**channel, "now": now}
    channel_values: dict[str, Any] = {}
    video_values: dict[str, dict[str, Any]] = {v["video_id"]: {} for v in videos}

    for m in _order(_select(metrics, only), metrics):
        if m.scope == "channel":
            kwargs = _channel_kwargs(
                m, metrics, channel_raw, videos, video_values, channel_values
            )
            scalars = [
                value
                for dep, value in kwargs.items()
                if not (dep in metrics and metrics[dep].scope == "video")
            ]
            channel_values[m.name] = (
                None if any(s is None for s in scalars) else m.fn(**kwargs)
            )
            continue
        for v in videos:
            derived = video_values[v["video_id"]]
            raw = {**v, "now": now}
            kwargs = _video_kwargs(m, metrics, raw, derived, channel_values)
            missing = any(value is None for value in kwargs.values())
            derived[m.name] = None if missing else m.fn(**kwargs)

    return Computed(channel=channel_values, videos=video_values)
