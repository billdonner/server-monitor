"""ServerCard — a reactive widget showing one server's metrics."""

from __future__ import annotations

from textual.reactive import reactive
from textual.widgets import Static

from .metric_row import render_metric_row


class ServerCard(Static):
    """Displays a single server's name, status, and metric rows.

    ``result`` is a dict matching ``{"metrics": [...]}`` or
    ``{"metrics": [], "error": "..."}`` as returned by collectors.
    """

    result: reactive[dict | None] = reactive(None)

    def __init__(self, server_name: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.server_name = server_name

    def render(self) -> str:
        r = self.result
        if r is None:
            return f"[bold cyan]{self.server_name}[/]  [dim]waiting...[/]"

        error = r.get("error")
        metrics = r.get("metrics", [])

        if error and not metrics:
            return f"[bold red]\u25cf[/] [bold]{self.server_name}[/]  [red]{error}[/]"

        # Header
        parts: list[str] = [f"[bold green]\u25cf[/] [bold]{self.server_name}[/]"]

        if error:
            parts[0] += f"  [yellow]{error}[/]"

        # Metric rows
        for m in metrics:
            parts.append(render_metric_row(m))

        return "\n".join(parts)

    def watch_result(self, new_val: dict | None) -> None:
        self.refresh()
