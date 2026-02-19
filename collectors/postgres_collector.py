"""Collector for PostgreSQL using pg_stat_* system views + custom YAML queries."""

from __future__ import annotations

from dataclasses import dataclass, field

import asyncpg

from .base import BaseCollector, CollectorResult, MetricItem, ServerInfo


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
        queries: list[CustomQuery] | None = None,
    ) -> None:
        super().__init__(name, poll_every)
        self.dsn = dsn
        self.queries = queries or []

    async def collect(self) -> CollectorResult:
        try:
            conn = await asyncpg.connect(self.dsn, timeout=5)
        except Exception as e:
            return CollectorResult(
                server=ServerInfo(name=self.name),
                metrics=[],
                error=f"Connect failed: {e}",
                reachable=False,
            )

        try:
            # Server version
            version_row = await conn.fetchval("SHOW server_version")
            version = str(version_row) if version_row else ""

            # Uptime
            uptime_row = await conn.fetchval(
                "SELECT EXTRACT(EPOCH FROM (now() - pg_postmaster_start_time()))::int"
            )
            uptime = int(uptime_row) if uptime_row else 0

            metrics: list[MetricItem] = []

            # -- pg_stat_database --
            db_stats = await conn.fetchrow(
                """SELECT
                    numbackends,
                    xact_commit,
                    xact_rollback,
                    blks_read,
                    blks_hit,
                    tup_returned,
                    tup_fetched,
                    tup_inserted,
                    tup_updated,
                    tup_deleted,
                    deadlocks,
                    temp_files
                FROM pg_stat_database
                WHERE datname = current_database()"""
            )
            if db_stats:
                metrics.append(
                    MetricItem(
                        key="active_connections",
                        label="Active Connections",
                        value=db_stats["numbackends"],
                        unit="conns",
                        warn_above=50,
                    )
                )
                metrics.append(
                    MetricItem(
                        key="transactions_committed",
                        label="Txn Committed",
                        value=db_stats["xact_commit"],
                        unit="count",
                    )
                )
                metrics.append(
                    MetricItem(
                        key="transactions_rolled_back",
                        label="Txn Rolled Back",
                        value=db_stats["xact_rollback"],
                        unit="count",
                        warn_above=100,
                    )
                )

                # Cache hit rate
                blks_hit = db_stats["blks_hit"]
                blks_read = db_stats["blks_read"]
                total = blks_hit + blks_read
                if total > 0:
                    hit_rate = round(blks_hit / total * 100, 2)
                    metrics.append(
                        MetricItem(
                            key="cache_hit_rate",
                            label="Cache Hit Rate",
                            value=hit_rate,
                            unit="%",
                            warn_below=99,
                        )
                    )

                metrics.append(
                    MetricItem(
                        key="deadlocks",
                        label="Deadlocks",
                        value=db_stats["deadlocks"],
                        unit="count",
                        warn_above=0,
                    )
                )
                metrics.append(
                    MetricItem(
                        key="temp_files",
                        label="Temp Files",
                        value=db_stats["temp_files"],
                        unit="count",
                        warn_above=100,
                    )
                )

            # -- Database size --
            db_size = await conn.fetchval(
                "SELECT pg_database_size(current_database())"
            )
            if db_size:
                metrics.append(
                    MetricItem(
                        key="db_size_mb",
                        label="Database Size",
                        value=round(db_size / 1_048_576, 1),
                        unit="MB",
                    )
                )

            # -- Custom YAML queries --
            for q in self.queries:
                try:
                    row = await conn.fetchrow(q.sql)
                    if row:
                        val = row.get("value", row[0]) if hasattr(row, "get") else row[0]
                        metrics.append(
                            MetricItem(
                                key=q.label.lower().replace(" ", "_").replace("(", "").replace(")", ""),
                                label=q.label,
                                value=val,
                                unit="count",
                                color=q.color,
                                warn_above=q.warn_above,
                                warn_below=q.warn_below,
                            )
                        )
                except Exception as e:
                    metrics.append(
                        MetricItem(
                            key=f"query_error_{q.label}",
                            label=f"{q.label} (error)",
                            value=str(e),
                        )
                    )

            await conn.close()

            return CollectorResult(
                server=ServerInfo(name=self.name, version=version, uptime_seconds=uptime),
                metrics=metrics,
            )

        except Exception as e:
            try:
                await conn.close()
            except Exception:
                pass
            return CollectorResult(
                server=ServerInfo(name=self.name),
                metrics=[],
                error=str(e),
                reachable=False,
            )
