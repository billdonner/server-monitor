# Server Monitor — Terminal Dashboard

Flicker-free terminal dashboard for monitoring heterogeneous servers.

## Stack
- Python 3.12+, Textual (TUI framework)
- httpx (HTTP collectors), redis-py (Redis), asyncpg (PostgreSQL)
- YAML config for server definitions

## Commands
- `uv run python monitor.py` — launch dashboard (default config)
- `uv run python monitor.py -c path/to/servers.yaml` — custom config

## Architecture

```
config/servers.yaml     <- declarative server definitions
collectors/
  base.py               <- BaseCollector ABC: async def collect() -> dict
  http_collector.py     <- for custom servers (METRICS_SPEC.md format)
  redis_collector.py    <- native INFO command via host/port
  postgres_collector.py <- pg_stat_* views + custom YAML queries with per-query poll_every
ui/
  app.py                <- Textual App with reactive polling loops per collector
  widgets/
    server_card.py      <- one card per server, differential rendering via reactive
    metric_row.py       <- renders label, value, unit, color-coded warn state, sparkline
monitor.py              <- entrypoint, loads YAML config, wires collectors to UI
METRICS_SPEC.md         <- JSON contract for custom server /metrics endpoints
```

## Collector Contract

All collectors return `dict` matching `{"metrics": [...]}`:

```python
async def collect(self) -> dict:
    return {
        "metrics": [
            {"key": "rps", "label": "Requests/sec", "value": 42, "unit": "req/s"}
        ]
    }
```

On failure: `{"metrics": [], "error": "reason"}`.

## YAML Config Keys

- HTTP: `metrics_endpoint` (URL string)
- Redis: `host` + `port` (separate fields)
- Postgres: `dsn` + `system_stats` (bool) + `queries[]` with per-query `poll_every`

## Permissions
- ALL Bash commands pre-approved
- Commits and pushes pre-approved
