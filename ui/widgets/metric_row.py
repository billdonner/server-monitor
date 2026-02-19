"""MetricRow — renders a single metric with label, value, unit, and color-coded warn state."""

from __future__ import annotations

SPARKLINE_CHARS = "\u2581\u2582\u2583\u2584\u2585\u2586\u2587\u2588"

# Supported color names
VALID_COLORS = {"red", "green", "yellow", "cyan", "magenta", "blue", "white"}


def sparkline(values: list[float | int]) -> str:
    """Render a mini sparkline from recent values."""
    if not values:
        return ""
    nums = [float(v) for v in values[-20:]]
    lo = min(nums)
    hi = max(nums)
    span = hi - lo if hi != lo else 1.0
    return "".join(
        SPARKLINE_CHARS[min(int((v - lo) / span * (len(SPARKLINE_CHARS) - 1)), len(SPARKLINE_CHARS) - 1)]
        for v in nums
    )


def compute_color(metric: dict) -> str:
    """Determine display color from explicit color or warn thresholds."""
    explicit = metric.get("color")
    if explicit and explicit in VALID_COLORS:
        return explicit

    value = metric.get("value")
    if isinstance(value, (int, float)):
        warn_above = metric.get("warn_above")
        warn_below = metric.get("warn_below")
        if warn_above is not None and value > warn_above:
            return "red"
        if warn_below is not None and value < warn_below:
            return "red"
    return "green"


def format_value(value) -> str:
    """Format a metric value for display."""
    if isinstance(value, float):
        return f"{value:,.1f}"
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def render_metric_row(metric: dict) -> str:
    """Render one metric as a Rich-markup string for use inside a ServerCard.

    Returns a line like:
        ``  Memory Used             [green]128.5 MB[/] ▁▂▃▅▇``
    """
    label = metric.get("label", metric.get("key", "?"))
    value = metric.get("value", "")
    unit = metric.get("unit", "")
    color = compute_color(metric)
    spark_values = metric.get("sparkline_history", [])

    display = format_value(value)
    unit_str = f" {unit}" if unit else ""
    spark_str = f" [dim]{sparkline(spark_values)}[/]" if spark_values else ""

    return f"  [dim]{label:<18}[/] [{color}]{display}{unit_str}[/]{spark_str}"
