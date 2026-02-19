# Server Monitor

Flicker-free terminal dashboard for monitoring heterogeneous servers — custom HTTP services, Redis, and PostgreSQL — in a single 2x2 grid view.

## Stack

- Python 3.12+, [Textual](https://textual.textualize.io/) (TUI framework)
- [httpx](https://www.python-httpx.org/) for HTTP polling
- [redis-py](https://redis-py.readthedocs.io/) async for Redis `INFO` introspection
- [asyncpg](https://magicstack.github.io/asyncpg/) for PostgreSQL `pg_stat_*` views + custom queries
- [PyYAML](https://pyyaml.org/) for declarative server configuration
- Package manager: [uv](https://docs.astral.sh/uv/)

## Quick Start

```bash
# Install dependencies
cd ~/server-monitor && uv sync

# Launch the dashboard (default config)
uv run python monitor.py

# Launch with a custom config
uv run python monitor.py -c path/to/servers.yaml
```

The dashboard opens in your terminal with a 2x2 grid of server cards. Each card polls its server independently and updates in place — no screen flicker.

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `r` | Refresh all servers immediately |
| `q` | Quit |

## Project Structure

| Path | Description |
|------|-------------|
| `monitor.py` | CLI entrypoint — parses YAML config, wires collectors to the TUI |
| `config/servers.yaml` | Declarative server definitions (edit this to add/remove servers) |
| `collectors/base.py` | `BaseCollector` ABC — async `collect() -> dict` contract |
| `collectors/http_collector.py` | Polls any server exposing `GET /metrics` (see METRICS_SPEC.md) |
| `collectors/redis_collector.py` | Native `INFO` command — clients, memory, ops/sec, hit rate, role |
| `collectors/postgres_collector.py` | `pg_stat_database` system views + custom SQL queries with per-query caching |
| `ui/app.py` | Textual `App` — 2x2 Grid layout, one async poll loop per collector |
| `ui/widgets/server_card.py` | Reactive card widget — waiting/error/healthy render states |
| `ui/widgets/metric_row.py` | Metric display — label, value, unit, color-coded warnings, sparklines |
| `METRICS_SPEC.md` | JSON contract for custom server `/metrics` endpoints |

## Configuration

Servers are defined in `config/servers.yaml`. Three collector types are supported:

### HTTP (custom servers)

Any server that exposes a `GET /metrics` endpoint returning the [METRICS_SPEC.md](METRICS_SPEC.md) JSON format.

```yaml
- name: "My API"
  type: http
  metrics_endpoint: "http://127.0.0.1:8000/metrics"
  poll_every: 15
```

### Redis

Connects directly via the Redis protocol and runs `INFO`.

```yaml
- name: "Redis"
  type: redis
  host: "localhost"
  port: 6379
  poll_every: 10
```

Metrics: Connected Clients (warn > 100), Memory Used MB (warn > 512), Ops/sec, Hit Rate % (warn < 90%), Role.

### PostgreSQL

Connects via `asyncpg` and queries `pg_stat_database` system views. Optionally runs custom SQL queries with independent poll intervals.

```yaml
- name: "Postgres"
  type: postgres
  dsn: "postgresql://user:pass@localhost:5432/mydb"
  system_stats: true
  poll_every: 15
  queries:
    - label: "Open Tasks"
      sql: "SELECT COUNT(*) as value FROM tasks WHERE status = 'open'"
      color: yellow
      warn_above: 100
      poll_every: 30
```

System metrics: Active Connections (warn > 50), Txn Committed, Txn Rolled Back (warn > 100), Cache Hit Rate % (warn < 99%), Deadlocks (warn > 0), Temp Files (warn > 100), Database Size MB.

### YAML Reference

| Field | Applies to | Required | Description |
|-------|-----------|----------|-------------|
| `name` | all | yes | Display name in the dashboard card |
| `type` | all | yes | `http`, `redis`, or `postgres` |
| `poll_every` | all | no | Seconds between polls (default: 5) |
| `metrics_endpoint` | http | yes | Full URL to `GET /metrics` |
| `host` | redis | no | Redis hostname (default: `localhost`) |
| `port` | redis | no | Redis port (default: `6379`) |
| `dsn` | postgres | yes | PostgreSQL connection string |
| `system_stats` | postgres | no | Query `pg_stat_database` (default: `true`) |
| `queries[]` | postgres | no | Custom SQL queries (see below) |

Custom query fields: `label` (display name), `sql` (must return a single `value` column), `color` (override), `warn_above`, `warn_below`, `poll_every` (independent interval).

## Adding Your Own Server

To monitor a new custom server, add a `GET /metrics` endpoint that returns the standard JSON format:

```json
{
  "metrics": [
    {"key": "rps", "label": "Requests/sec", "value": 42.5, "unit": "req/s"},
    {"key": "memory", "label": "Memory", "value": 128.5, "unit": "MB", "warn_above": 512}
  ]
}
```

Then add an entry to `config/servers.yaml`. See [METRICS_SPEC.md](METRICS_SPEC.md) for the full JSON contract with threshold colors, sparkline history, and implementation examples for FastAPI and Swift.

## Architecture

```
config/servers.yaml
        │
        ▼
   monitor.py ── load_config() ── instantiates collectors
        │
        ▼
   DashboardApp (Textual)
        │
        ├── Grid (2x2)
        │    ├── ServerCard[0] ◄── asyncio.Task(poll_loop) ◄── HttpCollector
        │    ├── ServerCard[1] ◄── asyncio.Task(poll_loop) ◄── HttpCollector
        │    ├── ServerCard[2] ◄── asyncio.Task(poll_loop) ◄── RedisCollector
        │    └── ServerCard[3] ◄── asyncio.Task(poll_loop) ◄── PostgresCollector
        │
        └── Each card renders: status dot + metrics via render_metric_row()
```

Each collector runs in its own `asyncio.Task` with independent poll intervals. Cards use Textual's `reactive` system — assigning a new result dict triggers a differential re-render with no screen flicker.

### Render States

| State | Indicator | When |
|-------|-----------|------|
| Waiting | `[cyan] waiting...` | Before first successful poll |
| Error | `[red] ●` + error message | Connection refused, timeout, etc. |
| Healthy | `[green] ●` + metric rows | Metrics received successfully |

### Color-Coded Warnings

Metric values are automatically colored based on thresholds:
- **Green** — value within normal range
- **Red** — value exceeds `warn_above` or falls below `warn_below`

## Default Configuration

The included `config/servers.yaml` monitors four servers:

| Server | Type | Port | Poll Interval |
|--------|------|------|---------------|
| Alities Engine | HTTP | 9847 | 15s |
| Nagzerver | HTTP | 9800 | 30s |
| Redis | Redis | 6379 | 10s |
| Postgres (Nagz) | Postgres | 5433 | 15s |

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| textual | >=3.0 | Terminal UI framework |
| httpx | >=0.28 | Async HTTP client |
| redis | >=5.2 | Async Redis client |
| asyncpg | >=0.30 | Async PostgreSQL driver |
| pyyaml | >=6.0 | YAML config parser |

## Related Repos

| Repo | Description |
|------|-------------|
| [alities-engine](https://github.com/billdonner/alities-engine) | Swift trivia engine (exposes `/metrics` on port 9847) |
| [nagzerver](https://github.com/billdonner/nagzerver) | Python API server (exposes `/metrics` on port 9800) |
