"""Collector for custom servers exposing GET /metrics (METRICS_SPEC.md format)."""

from __future__ import annotations

import httpx

from .base import BaseCollector, CollectorResult, MetricItem, ServerInfo


class HttpCollector(BaseCollector):
    def __init__(self, name: str, url: str, poll_every: int = 5) -> None:
        super().__init__(name, poll_every)
        self.url = url

    async def collect(self) -> CollectorResult:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(self.url)
                resp.raise_for_status()
                data = resp.json()

            # Parse server info
            srv = data.get("server", {})
            server = ServerInfo(
                name=srv.get("name", self.name),
                version=srv.get("version", ""),
                uptime_seconds=srv.get("uptime_seconds", 0),
            )

            # Parse metrics array
            metrics: list[MetricItem] = []
            for m in data.get("metrics", []):
                metrics.append(
                    MetricItem(
                        key=m.get("key", ""),
                        label=m.get("label", m.get("key", "")),
                        value=m.get("value", 0),
                        unit=m.get("unit", ""),
                        color=m.get("color"),
                        warn_above=m.get("warn_above"),
                        warn_below=m.get("warn_below"),
                        sparkline=m.get("sparkline", m.get("sparkline_history", [])) or [],
                    )
                )

            return CollectorResult(server=server, metrics=metrics)

        except httpx.ConnectError:
            return CollectorResult(
                server=ServerInfo(name=self.name),
                metrics=[],
                error="Connection refused",
                reachable=False,
            )
        except Exception as e:
            return CollectorResult(
                server=ServerInfo(name=self.name),
                metrics=[],
                error=str(e),
                reachable=False,
            )
