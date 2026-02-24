# Server Monitor

Monitoring dashboard for heterogeneous servers — custom HTTP services, Redis, and PostgreSQL. Available as both a **terminal TUI** (Textual) and a **browser-based web dashboard** (FastAPI).

**Live:** https://bd-server-monitor.fly.dev

## Stack

- Python 3.12+, [Textual](https://textual.textualize.io/) (TUI framework)
- [FastAPI](https://fastapi.tiangolo.com/) + [uvicorn](https://www.uvicorn.org/) (web dashboard)
- [httpx](https://www.python-httpx.org/) for HTTP polling
- [redis-py](https://redis-py.readthedocs.io/) async for Redis `INFO` introspection
- [asyncpg](https://magicstack.github.io/asyncpg/) for PostgreSQL `pg_stat_*` views + custom queries
- [PyYAML](https://pyyaml.org/) for declarative server configuration
- Package manager: [uv](https://docs.astral.sh/uv/)

## Quick Start

```bash
# Install dependencies
cd ~/server-monitor && uv sync

# Launch the terminal dashboard (default config)
uv run python monitor.py

# Launch the web dashboard (opens at http://127.0.0.1:9860)
uv run python web.py

# Custom config / port
uv run python monitor.py -c path/to/servers.yaml
uv run python web.py -c path/to/servers.yaml --port 8080
```

The terminal dashboard opens with a 2x2 grid of server cards. The web dashboard opens in your browser with selectable 1/2/3 column layouts. Both poll servers independently with no flicker.

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Ctrl+P` | Open command palette |
| `R` | Refresh all servers immediately |
| `1` / `2` / `3` | Set 1, 2, or 3 column layout |
| `T` | Toggle dark/light theme |
| `M` | Mini player mode |
| `Q` | Quit (TUI only) |

## Project Structure

| Path | Description |
|------|-------------|
| `monitor.py` | TUI entrypoint — parses YAML config, wires collectors to Textual |
| `web.py` | Web entrypoint — FastAPI + uvicorn, serves API + static frontend |
| `config/servers.yaml` | Declarative server definitions (edit this to add/remove servers) |
| `collectors/base.py` | `BaseCollector` ABC — async `collect() -> dict` contract |
| `collectors/http_collector.py` | Polls any server exposing `GET /metrics` (see METRICS_SPEC.md) |
| `collectors/redis_collector.py` | Native `INFO` command — clients, memory, ops/sec, hit rate, role |
| `collectors/postgres_collector.py` | `pg_stat_database` system views + custom SQL queries with per-query caching |
| `ui/app.py` | Textual `App` — 2x2 Grid layout, one async poll loop per collector |
| `ui/widgets/server_card.py` | Reactive card widget — waiting/error/healthy render states |
| `ui/widgets/metric_row.py` | Metric display — label, value, unit, color-coded warnings, sparklines |
| `static/index.html` | Self-contained web frontend (HTML + CSS + JS, no build step) |
| `static/help.html` | Usage guide — keyboard shortcuts, metric colors, server table |
| `METRICS_SPEC.md` | JSON contract for custom server `/metrics` endpoints |

## Configuration

Servers are defined in `config/servers.yaml`. Three collector types are supported:

### HTTP (custom servers)

Any server that exposes a `GET /metrics` endpoint returning the [METRICS_SPEC.md](METRICS_SPEC.md) JSON format.

```yaml
- name: "My API"
  type: http
  metrics_endpoint: "http://127.0.0.1:8000/metrics"
  web_url: "https://my-api.fly.dev"
  poll_every: 15
```

The optional `web_url` field adds a clickable link on the card to the server's web interface.

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
| `web_url` | http | no | Clickable link to the server's web interface |
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

## Web Dashboard

The web dashboard (`web.py`) provides the same monitoring in your browser:

- **Dark theme** matching the terminal version — colored status dots, green/red metric values, sparklines
- **Selectable grid layout** — toolbar buttons for 1, 2, or 3 columns (saved to localStorage)
- **Auto-refresh** — polls `/api/status` every 3 seconds
- **Web app links** — clickable URLs to each server's web interface (when `web_url` configured)
- **Help page** — accessible from toolbar, documents keyboard shortcuts and card indicators
- **Command palette** — `Ctrl+P` opens a searchable command list
- **Mini player** — compact status-bar-only popup window
- **Zero build step** — single self-contained `static/index.html` (no npm/webpack/vite)
- **Same config** — reads the same `config/servers.yaml` as the terminal version

### API

`GET /api/status` returns the current state of all monitored servers:

```json
{
  "servers": [
    {
      "name": "card-engine",
      "url": "http://127.0.0.1:9810/metrics",
      "web_url": "https://bd-card-engine.fly.dev",
      "poll_every": 15,
      "last_updated": 1708380000.4,
      "metrics": [{"key": "total_cards", "label": "Total Cards", "value": 105, "unit": "count"}],
      "error": null
    }
  ],
  "timestamp": 1708380001.2,
  "lan_ip": "192.168.1.100"
}
```

## Default Configuration

The included `config/servers.yaml` monitors six servers:

| Server | Type | Port | Poll Interval | Web App |
|--------|------|------|---------------|---------|
| card-engine | HTTP | 9810 | 15s | https://bd-card-engine.fly.dev |
| Nagzerver | HTTP | 9800 | 30s | https://bd-nagzerver.fly.dev |
| Server Monitor | HTTP | 9860 | 10s | https://bd-server-monitor.fly.dev |
| Redis | Redis | 6379 | 10s | — |
| Postgres (Nagz) | Postgres | 5433 | 15s | — |
| Advice App | HTTP | 9820 | 15s | — |

## Deployment

Deployed to [Fly.io](https://fly.io) via the [Flyz](https://github.com/billdonner/Flyz) infrastructure repo:

```bash
~/Flyz/scripts/deploy.sh server-monitor
```

The production config at `~/Flyz/apps/server-monitor/config/servers.yaml` polls Fly.io public URLs instead of localhost.

## Architecture

```
config/servers.yaml
        │
        ▼
   load_config() ── instantiates collectors
        │
   ┌────┴────┐
   ▼         ▼
monitor.py  web.py
(Textual)   (FastAPI)
   │         │
   ▼         ▼
DashboardApp  uvicorn ── GET /api/status ── static/index.html
   │
   ├── Grid (2x2)
   │    ├── ServerCard[0] ◄── asyncio.Task ◄── HttpCollector
   │    ├── ServerCard[1] ◄── asyncio.Task ◄── HttpCollector
   │    ├── ServerCard[2] ◄── asyncio.Task ◄── RedisCollector
   │    └── ServerCard[3] ◄── asyncio.Task ◄── PostgresCollector
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

## Related Repos

| Repo | Description |
|------|-------------|
| [card-engine](https://github.com/billdonner/card-engine) | Unified flashcard + trivia backend (exposes `/metrics` on port 9810) |
| [nagzerver](https://github.com/billdonner/nagzerver) | Python API server (exposes `/metrics` on port 9800) |
| [server-monitor-ios](https://github.com/billdonner/server-monitor-ios) | SwiftUI iOS + WidgetKit companion app |
| [Flyz](https://github.com/billdonner/Flyz) | Fly.io deployment configs |
