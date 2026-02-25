"""Collector for Redis servers using the native INFO command."""

from __future__ import annotations

import redis.asyncio as aioredis

from .base import BaseCollector


class RedisCollector(BaseCollector):
    def __init__(self, name: str, host: str = "localhost", port: int = 6379, url: str | None = None, poll_every: int = 10) -> None:
        display = url or f"{host}:{port}"
        super().__init__(name, poll_every, url=display)
        self.redis_url = url
        self.host = host
        self.port = port

    async def collect(self) -> dict:
        try:
            if self.redis_url:
                r = aioredis.from_url(self.redis_url, decode_responses=True, socket_timeout=5)
            else:
                r = aioredis.Redis(host=self.host, port=self.port, decode_responses=True, socket_timeout=3)
            info = await r.info()
            await r.aclose()
        except Exception as e:
            return {"metrics": [], "error": str(e)}

        # Compute hit rate
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total = hits + misses
        hit_rate = round(hits / total * 100, 1) if total > 0 else None

        metrics = [
            {
                "key": "connected_clients",
                "label": "Clients",
                "value": info.get("connected_clients", 0),
                "unit": "clients",
                "warn_above": 100,
            },
            {
                "key": "used_memory_mb",
                "label": "Memory",
                "value": round(info.get("used_memory", 0) / 1_048_576, 1),
                "unit": "MB",
                "warn_above": 512,
            },
            {
                "key": "ops_per_sec",
                "label": "Ops/sec",
                "value": info.get("instantaneous_ops_per_sec", 0),
                "unit": "ops/s",
            },
        ]

        if hit_rate is not None:
            metrics.append({
                "key": "hit_rate",
                "label": "Hit Rate",
                "value": hit_rate,
                "unit": "%",
                "warn_below": 90,
            })

        metrics.append({
            "key": "role",
            "label": "Role",
            "value": info.get("role", "unknown"),
        })

        return {"metrics": metrics}
