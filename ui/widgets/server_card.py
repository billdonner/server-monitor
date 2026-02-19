"""ServerCard — a reactive widget showing one server's metrics."""

from __future__ import annotations

from rich.markup import escape

from textual.reactive import reactive
from textual.widgets import Static

from .metric_row import render_metric_row


class ServerCard(Static):
    """Displays a single server's name, status, and metric rows.

    ``result`` is a dict matching ``{"metrics": [...]}`` or
    ``{"metrics": [], "error": "..."}`` as returned by collectors.
    """

    result: reactive[dict | None] = reactive(None)

    def __init__(self, server_name: str, url: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self.server_name = server_name
        self.server_url = url

    def render(self) -> str:
        r = self.result
        parts: list[str] = []

        if r is None:
            parts.append(f"[bold cyan]{self.server_name}[/]  [dim]waiting...[/]")
            if self.server_url:
                parts.append(f"  [dim]{escape(self.server_url)}[/]")
            return "\n".join(parts)

        error = r.get("error")
        metrics = r.get("metrics", [])

        if error and not metrics:
            parts.append(f"[bold red]\u25cf[/] [bold]{self.server_name}[/]  [red]{error}[/]")
            if self.server_url:
                parts.append(f"  [dim]{escape(self.server_url)}[/]")
            return "\n".join(parts)

        # Header
        parts.append(f"[bold green]\u25cf[/] [bold]{self.server_name}[/]")
        if self.server_url:
            parts.append(f"  [dim]{escape(self.server_url)}[/]")

        if error:
            parts[0] += f"  [yellow]{error}[/]"

        # Metric rows
        for m in metrics:
            parts.append(render_metric_row(m))

        return "\n".join(parts)

    def watch_result(self, new_val: dict | None) -> None:
        self.refresh(layout=True)
