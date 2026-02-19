"""ServerCard — a reactive widget showing one server's metrics."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widgets import Static

from collectors.base import CollectorResult, MetricItem

# Textual CSS color names matching METRICS_SPEC colors
COLOR_MAP = {
    "red": "red",
    "green": "green",
    "yellow": "yellow",
    "cyan": "cyan",
    "magenta": "magenta",
    "blue": "blue",
    "white": "white",
}

SPARKLINE_CHARS = "▁▂▃▄▅▆▇█"


def _sparkline(values: list[float]) -> str:
    """Render a mini sparkline from recent values."""
    if not values:
        return ""
    lo = min(values)
    hi = max(values)
    span = hi - lo if hi != lo else 1
    return "".join(
        SPARKLINE_CHARS[min(int((v - lo) / span * (len(SPARKLINE_CHARS) - 1)), len(SPARKLINE_CHARS) - 1)]
        for v in values[-20:]  # last 20 points
    )


class ServerCard(Static):
    """Displays a single server's name, status, and metric rows."""

    result: reactive[CollectorResult | None] = reactive(None)

    def __init__(self, server_name: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.server_name = server_name

    def render(self) -> str:
        r = self.result
        if r is None:
            return f"[bold cyan]{self.server_name}[/]  [dim]waiting...[/]"

        # Header
        parts: list[str] = []
        if r.reachable:
            status = "[bold green]●[/]"
            ver = f" [dim]v{r.server.version}[/]" if r.server.version else ""
            up_h = r.server.uptime_seconds // 3600
            up_m = (r.server.uptime_seconds % 3600) // 60
            uptime = f" [dim]up {up_h}h{up_m}m[/]" if r.server.uptime_seconds else ""
            parts.append(f"{status} [bold]{r.server.name}[/]{ver}{uptime}")
        else:
            parts.append(f"[bold red]●[/] [bold]{self.server_name}[/]  [red]{r.error or 'unreachable'}[/]")
            return "\n".join(parts)

        # Metrics rows
        for m in r.metrics:
            color = COLOR_MAP.get(m.display_color, "white")
            spark = ""
            if m.sparkline:
                spark = f" [dim]{_sparkline(m.sparkline)}[/]"
            unit = f" {m.unit}" if m.unit else ""
            parts.append(f"  [dim]{m.label:<24}[/] [{color}]{m.display_value}{unit}[/]{spark}")

        return "\n".join(parts)

    def watch_result(self, new_val: CollectorResult | None) -> None:
        """Called automatically when self.result changes — triggers re-render."""
        self.refresh()
