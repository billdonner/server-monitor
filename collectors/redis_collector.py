"""Collector for Redis servers using the native INFO command."""

from __future__ import annotations

import redis.asyncio as aioredis

from .base import BaseCollector


class RedisCollector(BaseCollector):
    def __init__(self, name: str, host: str = "localhost", port: int = 6379, poll_every: int = 10) -> None:
        super().__init__(name, poll_every, url=f"{host}:{port}")
        self.host = host
        self.port = port

    async def collect(self) -> dict:
        try:
            r = aioredis.Redis(host=self.host, port=self.port, decode_responses=True, socket_timeout=3)
            info = await r.info()
            await r.aclose()
        except Exception as e:
            return {"metrics": [], "error": str(e)}

        metrics = [
            {
                "key": "connected_clients",
                "label": "Connected Clients",
                "value": info.get("connected_clients", 0),
                "unit": "clients",
                "warn_above": 100,
            },
            {
                "key": "used_memory_mb",
                "label": "Memory Used",
                "value": round(info.get("used_memory", 0) / 1_048_576, 1),
                "unit": "MB",
                "warn_above": 512,
            },
            {
                "key": "used_memory_peak_mb",
                "label": "Memory Peak",
                "value": round(info.get("used_memory_peak", 0) / 1_048_576, 1),
                "unit": "MB",
            },
            {
                "key": "ops_per_sec",
                "label": "Ops/sec",
                "value": info.get("instantaneous_ops_per_sec", 0),
                "unit": "ops/s",
            },
            {
                "key": "total_connections",
                "label": "Total Connections",
                "value": info.get("total_connections_received", 0),
                "unit": "count",
            },
            {
                "key": "keyspace_hits",
                "label": "Keyspace Hits",
                "value": info.get("keyspace_hits", 0),
                "unit": "count",
            },
            {
                "key": "keyspace_misses",
                "label": "Keyspace Misses",
                "value": info.get("keyspace_misses", 0),
                "unit": "count",
            },
        ]

        # Compute hit rate
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total = hits + misses
        if total > 0:
            metrics.append({
                "key": "hit_rate",
                "label": "Hit Rate",
                "value": round(hits / total * 100, 1),
                "unit": "%",
                "warn_below": 90,
            })

        metrics.append({
            "key": "role",
            "label": "Role",
            "value": info.get("role", "unknown"),
        })

        return {"metrics": metrics}
