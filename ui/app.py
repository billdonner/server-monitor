"""Textual dashboard app — flicker-free reactive terminal UI."""

from __future__ import annotations

import asyncio
import re

from textual.app import App, ComposeResult
from textual.containers import Grid
from textual.reactive import reactive
from textual.widgets import Header, Footer, Static

from collectors.base import BaseCollector
from ui.widgets.server_card import ServerCard


class StatusBar(Static):
    """Colored status bar showing aggregate server health."""

    status: reactive[str] = reactive("waiting")
    detail: reactive[str] = reactive("")

    def render(self) -> str:
        if self.status == "ok":
            return f"[bold white on green] All Systems OK [/]  [green]{self.detail}[/]"
        elif self.status == "error":
            return f"[bold white on red] {self.detail} [/]"
        return "[dim]Waiting for server data...[/]"

    def watch_status(self, new_val: str) -> None:
        self.refresh()

    def watch_detail(self, new_val: str) -> None:
        self.refresh()


class DashboardApp(App):
    """Server monitoring dashboard with differential rendering."""

    CSS = """
    Screen {
        background: $surface;
    }
    #status-bar {
        height: 1;
        width: 1fr;
        padding: 0 2;
    }
    #dashboard-grid {
        grid-size: 2 2;
        grid-gutter: 1 2;
        padding: 1 2;
        width: 1fr;
        height: 1fr;
    }
    ServerCard {
        padding: 1 2;
        background: $panel;
        border: round $primary;
        width: 1fr;
        height: 1fr;
    }
    ServerCard.error-state {
        border: heavy red;
    }
    .hidden {
        display: none;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh Now"),
        ("m", "toggle_mini", "Mini Player"),
    ]

    def __init__(self, collectors: list[BaseCollector]) -> None:
        super().__init__()
        self.collectors = collectors
        self._cards: dict[str, ServerCard] = {}
        self._tasks: list[asyncio.Task] = []
        self._status_bar: StatusBar | None = None
        self._mini_mode: bool = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        self._status_bar = StatusBar(id="status-bar")
        yield self._status_bar
        with Grid(id="dashboard-grid"):
            for c in self.collectors:
                safe_id = re.sub(r'[^a-z0-9_-]', '', c.name.lower().replace(' ', '-'))
                card = ServerCard(c.name, url=c.url, id=f"card-{safe_id}")
                self._cards[c.name] = card
                yield card
        yield Footer()

    def on_mount(self) -> None:
        for collector in self.collectors:
            task = asyncio.create_task(self._poll_loop(collector))
            self._tasks.append(task)

    def _update_status_bar(self) -> None:
        """Recompute aggregate status from all cards."""
        if self._status_bar is None:
            return
        error_names: list[str] = []
        total = 0
        for name, card in self._cards.items():
            r = card.result
            if r is None:
                continue
            total += 1
            if r.get("error"):
                error_names.append(name)

        if total == 0:
            self._status_bar.status = "waiting"
            self._status_bar.detail = ""
        elif error_names:
            count = len(error_names)
            label = f"{count} Server{'s' if count > 1 else ''} Down"
            self._status_bar.status = "error"
            self._status_bar.detail = f"{label} \u2014 {', '.join(error_names)}"
        else:
            self._status_bar.status = "ok"
            self._status_bar.detail = f"{total}/{total} servers healthy"

    async def _poll_loop(self, collector: BaseCollector) -> None:
        card = self._cards[collector.name]
        while True:
            result = await collector.collect()
            card.result = result
            self._update_status_bar()
            await asyncio.sleep(collector.poll_every)

    def action_toggle_mini(self) -> None:
        """Toggle between mini (status bar only) and full dashboard."""
        self._mini_mode = not self._mini_mode
        grid = self.query_one("#dashboard-grid")
        header = self.query_one("Header")
        grid.set_class(self._mini_mode, "hidden")
        header.set_class(self._mini_mode, "hidden")

    def action_refresh(self) -> None:
        for collector in self.collectors:
            asyncio.create_task(self._poll_once(collector))

    async def _poll_once(self, collector: BaseCollector) -> None:
        card = self._cards[collector.name]
        result = await collector.collect()
        card.result = result
        self._update_status_bar()

    def on_unmount(self) -> None:
        for task in self._tasks:
            task.cancel()
