"""Collector for Redis servers using the native INFO command."""

from __future__ import annotations

import redis.asyncio as aioredis

from .base import BaseCollector, CollectorResult, MetricItem, ServerInfo


class RedisCollector(BaseCollector):
    def __init__(self, name: str, url: str, poll_every: int = 10) -> None:
        super().__init__(name, poll_every)
        self.url = url

    async def collect(self) -> CollectorResult:
        try:
            r = aioredis.from_url(self.url, decode_responses=True, socket_timeout=3)
            info = await r.info()
            await r.aclose()

            version = info.get("redis_version", "")
            uptime = info.get("uptime_in_seconds", 0)

            metrics = [
                MetricItem(
                    key="connected_clients",
                    label="Connected Clients",
                    value=info.get("connected_clients", 0),
                    unit="clients",
                    warn_above=100,
                ),
                MetricItem(
                    key="used_memory_mb",
                    label="Memory Used",
                    value=round(info.get("used_memory", 0) / 1_048_576, 1),
                    unit="MB",
                    warn_above=512,
                ),
                MetricItem(
                    key="used_memory_peak_mb",
                    label="Memory Peak",
                    value=round(info.get("used_memory_peak", 0) / 1_048_576, 1),
                    unit="MB",
                ),
                MetricItem(
                    key="ops_per_sec",
                    label="Ops/sec",
                    value=info.get("instantaneous_ops_per_sec", 0),
                    unit="ops/s",
                ),
                MetricItem(
                    key="total_connections",
                    label="Total Connections",
                    value=info.get("total_connections_received", 0),
                    unit="count",
                ),
                MetricItem(
                    key="keyspace_hits",
                    label="Keyspace Hits",
                    value=info.get("keyspace_hits", 0),
                    unit="count",
                ),
                MetricItem(
                    key="keyspace_misses",
                    label="Keyspace Misses",
                    value=info.get("keyspace_misses", 0),
                    unit="count",
                ),
            ]

            # Compute hit rate
            hits = info.get("keyspace_hits", 0)
            misses = info.get("keyspace_misses", 0)
            total = hits + misses
            if total > 0:
                hit_rate = round(hits / total * 100, 1)
                metrics.append(
                    MetricItem(
                        key="hit_rate",
                        label="Hit Rate",
                        value=hit_rate,
                        unit="%",
                        warn_below=90,
                    )
                )

            metrics.append(
                MetricItem(
                    key="role",
                    label="Role",
                    value=info.get("role", "unknown"),
                )
            )

            return CollectorResult(
                server=ServerInfo(name=self.name, version=version, uptime_seconds=uptime),
                metrics=metrics,
            )

        except Exception as e:
            return CollectorResult(
                server=ServerInfo(name=self.name),
                metrics=[],
                error=str(e),
                reachable=False,
            )
