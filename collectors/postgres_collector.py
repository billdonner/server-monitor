"""Collector for PostgreSQL using pg_stat_* system views + custom YAML queries."""

from __future__ import annotations

import time
from dataclasses import dataclass

import asyncpg

from .base import BaseCollector


@dataclass
class CustomQuery:
    label: str
    sql: str
    color: str | None = None
    warn_above: float | None = None
    warn_below: float | None = None
    poll_every: int = 15


class PostgresCollector(BaseCollector):
    def __init__(
        self,
        name: str,
        dsn: str,
        poll_every: int = 15,
        system_stats: bool = True,
        queries: list[CustomQuery] | None = None,
    ) -> None:
        super().__init__(name, poll_every, url=dsn)
        self.dsn = dsn
        self.system_stats = system_stats
        self.queries = queries or []
        # Per-query result cache: {label: (last_run_time, metric_dict)}
        self._query_cache: dict[str, tuple[float, dict]] = {}

    async def collect(self) -> dict:
        try:
            conn = await asyncpg.connect(self.dsn, timeout=5)
        except Exception as e:
            return {"metrics": [], "error": f"Connect failed: {e}"}

        try:
            metrics: list[dict] = []

            # -- System stats (pg_stat_*) --
            if self.system_stats:
                db_stats = await conn.fetchrow(
                    """SELECT
                        numbackends,
                        xact_commit,
                        xact_rollback,
                        blks_read,
                        blks_hit,
                        deadlocks,
                        temp_files
                    FROM pg_stat_database
                    WHERE datname = current_database()"""
                )
                if db_stats:
                    metrics.append({
                        "key": "active_connections",
                        "label": "Active Connections",
                        "value": db_stats["numbackends"],
                        "unit": "conns",
                        "warn_above": 50,
                    })
                    metrics.append({
                        "key": "txn_committed",
                        "label": "Txn Committed",
                        "value": db_stats["xact_commit"],
                        "unit": "count",
                    })
                    metrics.append({
                        "key": "txn_rolled_back",
                        "label": "Txn Rolled Back",
                        "value": db_stats["xact_rollback"],
                        "unit": "count",
                        "warn_above": 100,
                    })

                    blks_hit = db_stats["blks_hit"]
                    blks_read = db_stats["blks_read"]
                    total = blks_hit + blks_read
                    if total > 0:
                        metrics.append({
                            "key": "cache_hit_rate",
                            "label": "Cache Hit Rate",
                            "value": round(blks_hit / total * 100, 2),
                            "unit": "%",
                            "warn_below": 99,
                        })

                    metrics.append({
                        "key": "deadlocks",
                        "label": "Deadlocks",
                        "value": db_stats["deadlocks"],
                        "unit": "count",
                        "warn_above": 0,
                    })
                    metrics.append({
                        "key": "temp_files",
                        "label": "Temp Files",
                        "value": db_stats["temp_files"],
                        "unit": "count",
                        "warn_above": 100,
                    })

                db_size = await conn.fetchval(
                    "SELECT pg_database_size(current_database())"
                )
                if db_size:
                    metrics.append({
                        "key": "db_size_mb",
                        "label": "Database Size",
                        "value": round(db_size / 1_048_576, 1),
                        "unit": "MB",
                    })

            # -- Custom YAML queries (with per-query poll_every) --
            now = time.monotonic()
            for q in self.queries:
                cache_entry = self._query_cache.get(q.label)
                if cache_entry and (now - cache_entry[0]) < q.poll_every:
                    # Use cached result
                    metrics.append(cache_entry[1])
                    continue

                try:
                    row = await conn.fetchrow(q.sql)
                    if row:
                        val = row[0]
                        metric = {
                            "key": q.label.lower().replace(" ", "_").replace("(", "").replace(")", ""),
                            "label": q.label,
                            "value": val,
                            "unit": "count",
                        }
                        if q.color:
                            metric["color"] = q.color
                        if q.warn_above is not None:
                            metric["warn_above"] = q.warn_above
                        if q.warn_below is not None:
                            metric["warn_below"] = q.warn_below
                        self._query_cache[q.label] = (now, metric)
                        metrics.append(metric)
                except Exception as e:
                    metrics.append({
                        "key": f"query_error",
                        "label": f"{q.label} (error)",
                        "value": str(e),
                    })

            await conn.close()
            return {"metrics": metrics}

        except Exception as e:
            try:
                await conn.close()
            except Exception:
                pass
            return {"metrics": [], "error": str(e)}
