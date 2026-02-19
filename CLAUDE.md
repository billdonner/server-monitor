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
config/servers.yaml     ← declarative server definitions
collectors/
  base.py               ← BaseCollector ABC + data types
  http_collector.py     ← for custom servers (METRICS_SPEC.md format)
  redis_collector.py    ← native INFO command
  postgres_collector.py ← pg_stat_* views + custom YAML queries
ui/
  app.py                ← Textual App with reactive polling
  widgets/
    server_card.py      ← one card per server, differential rendering
monitor.py              ← entrypoint, loads config, wires everything
METRICS_SPEC.md         ← contract for custom server /metrics endpoints
```

## Adding a Custom Server

1. Add a `/metrics` endpoint to your server (see METRICS_SPEC.md)
2. Add an entry to `config/servers.yaml`
3. Restart the dashboard

## Monitored Servers

| Server | Type | URL | Poll |
|--------|------|-----|------|
| Alities Engine | http | localhost:9847/metrics | 5s |
| Nagzerver | http | localhost:9800/api/v1/metrics | 5s |
| Redis | redis | localhost:6379 | 10s |
| Postgres (Nagz) | postgres | localhost:5433/nagz | 15s |

## Permissions
- ALL Bash commands pre-approved
- Commits and pushes pre-approved
