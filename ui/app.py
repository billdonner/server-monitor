"""Textual dashboard app — flicker-free reactive terminal UI."""

from __future__ import annotations

import asyncio

from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Header, Footer, Static

from collectors.base import BaseCollector
from ui.widgets.server_card import ServerCard


class DashboardApp(App):
    """Server monitoring dashboard with differential rendering."""

    CSS = """
    Screen {
        background: $surface;
    }
    VerticalScroll {
        padding: 1 2;
    }
    ServerCard {
        margin-bottom: 1;
        padding: 1 2;
        background: $panel;
        border: round $primary;
        width: 100%;
    }
    #title-bar {
        dock: top;
        height: 1;
        background: $accent;
        color: $text;
        text-align: center;
        text-style: bold;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh Now"),
    ]

    def __init__(self, collectors: list[BaseCollector]) -> None:
        super().__init__()
        self.collectors = collectors
        self._cards: dict[str, ServerCard] = {}
        self._tasks: list[asyncio.Task] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with VerticalScroll():
            for c in self.collectors:
                card = ServerCard(c.name, id=f"card-{c.name.lower().replace(' ', '-')}")
                self._cards[c.name] = card
                yield card
        yield Footer()

    def on_mount(self) -> None:
        """Start a polling loop for each collector."""
        for collector in self.collectors:
            task = asyncio.create_task(self._poll_loop(collector))
            self._tasks.append(task)

    async def _poll_loop(self, collector: BaseCollector) -> None:
        """Continuously poll a collector and update its card."""
        card = self._cards[collector.name]
        while True:
            result = await collector.collect()
            card.result = result
            await asyncio.sleep(collector.poll_every)

    def action_refresh(self) -> None:
        """Force an immediate refresh of all collectors."""
        for collector in self.collectors:
            asyncio.create_task(self._poll_once(collector))

    async def _poll_once(self, collector: BaseCollector) -> None:
        card = self._cards[collector.name]
        result = await collector.collect()
        card.result = result

    def on_unmount(self) -> None:
        for task in self._tasks:
            task.cancel()
