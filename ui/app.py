"""Textual dashboard app — flicker-free reactive terminal UI."""

from __future__ import annotations

import asyncio
import re

from textual.app import App, ComposeResult
from textual.containers import Grid
from textual.widgets import Header, Footer

from collectors.base import BaseCollector
from ui.widgets.server_card import ServerCard


class DashboardApp(App):
    """Server monitoring dashboard with differential rendering."""

    CSS = """
    Screen {
        background: $surface;
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

    async def _poll_loop(self, collector: BaseCollector) -> None:
        card = self._cards[collector.name]
        while True:
            result = await collector.collect()
            card.result = result
            await asyncio.sleep(collector.poll_every)

    def action_refresh(self) -> None:
        for collector in self.collectors:
            asyncio.create_task(self._poll_once(collector))

    async def _poll_once(self, collector: BaseCollector) -> None:
        card = self._cards[collector.name]
        result = await collector.collect()
        card.result = result

    def on_unmount(self) -> None:
        for task in self._tasks:
            task.cancel()
