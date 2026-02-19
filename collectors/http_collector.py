"""Collector for custom servers exposing GET /metrics (METRICS_SPEC.md format)."""

from __future__ import annotations

import httpx

from .base import BaseCollector


class HttpCollector(BaseCollector):
    def __init__(self, name: str, metrics_endpoint: str, poll_every: int = 5) -> None:
        super().__init__(name, poll_every)
        self.metrics_endpoint = metrics_endpoint

    async def collect(self) -> dict:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(self.metrics_endpoint)
                resp.raise_for_status()
                data = resp.json()

            # Normalize: ensure metrics key exists
            metrics = data.get("metrics", [])
            return {"metrics": metrics}

        except httpx.ConnectError:
            return {"metrics": [], "error": "Connection refused"}
        except Exception as e:
            return {"metrics": [], "error": str(e)}
