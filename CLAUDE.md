# Server Monitor — Terminal Dashboard

Flicker-free terminal dashboard for monitoring heterogeneous servers (HTTP, Redis, PostgreSQL) in a 2x2 grid layout.

**Live URL:** https://bd-server-monitor.fly.dev

**Four frontends share the same backend:**
- Terminal TUI (`monitor.py`) — Textual framework
- Web dashboard (`web.py`) — FastAPI + static HTML on port 9860
- iOS app (`~/server-monitor-ios`) — SwiftUI + WidgetKit (iOS 18.5+)
- watchOS app (`~/server-monitor-ios`) — SwiftUI + WidgetKit complications (watchOS 10+)

## Stack

- Python 3.12+, [Textual](https://textual.textualize.io/) (TUI framework)
- httpx (HTTP collectors), redis-py (Redis), asyncpg (PostgreSQL)
- YAML config for server definitions
- Package manager: [uv](https://docs.astral.sh/uv/)

## Commands

| Command | Description |
|---------|-------------|
| `uv run python monitor.py` | Launch terminal dashboard (default config) |
| `uv run python monitor.py -c path/to/servers.yaml` | Launch terminal with custom config |
| `uv run python web.py` | Launch web dashboard on port 9860 |
| `uv run python web.py -c path/to/servers.yaml --port 8080` | Web dashboard with custom config/port |
| `uv sync` | Install/update dependencies |

## Architecture

```
config/servers.yaml     <- declarative server definitions
collectors/
  base.py               <- BaseCollector ABC: async def collect() -> dict
  http_collector.py     <- for custom servers (METRICS_SPEC.md format)
  redis_collector.py    <- native INFO command via host/port (5 metrics)
  postgres_collector.py <- pg_stat_* views + custom YAML queries with per-query poll_every
ui/
  app.py                <- Textual App, 2x2 Grid layout, async poll loops per collector
  widgets/
    server_card.py      <- one card per server, 3 render states (waiting/error/ok)
    metric_row.py       <- renders label (18-char), value, unit, warn color, sparkline
static/
  index.html            <- self-contained web frontend (HTML + CSS + JS, no build step)
  help.html             <- usage guide (keyboard shortcuts, metric colors, server table)
monitor.py              <- TUI entrypoint, loads YAML config, wires collectors to Textual
web.py                  <- Web entrypoint, FastAPI + uvicorn, serves API + static frontend
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

On failure: `{"metrics": [], "error": "reason"}`. Must never raise.

## YAML Config Keys

| Type | Required Fields | Optional Fields |
|------|----------------|-----------------|
| HTTP | `metrics_endpoint` (URL) | `poll_every`, `web_url` |
| Redis | — | `host`, `port`, `poll_every` |
| Postgres | `dsn` | `system_stats`, `queries[]` with per-query `poll_every` |

The `web_url` field adds a clickable link on the server card to the app's web interface.

## Error Highlighting

All three frontends highlight unreachable servers with red borders:
- **Web**: 2px red border + red glow (`card-error-border` class)
- **Terminal**: `heavy red` border via `error-state` CSS class
- **iOS**: 2pt red stroke + shadow overlay on `ServerCardView`

## Sticky Yellow Warning State

When a server fails and later recovers, it enters a "warned" (yellow) state instead of going straight to green. This makes it visible that something went wrong, even after recovery.

- Backend tracks `_ever_failed: set[str]` — servers that have errored at least once
- Each server snapshot includes `had_error: bool` in the `/api/status` response
- `POST /api/clear-warnings` clears the sticky state for all servers
- **Web dashboard**: yellow banner, yellow card border (`card-warning-border`), yellow dot; `C` key or toolbar button to clear
- **Mini player**: yellow pulse dot, yellow server dots; `C` key or context menu to clear
- **iOS app**: yellow card border, yellow banner, "Clear" button in header
- `/metrics` includes `servers_warned` count

## Key Design Decisions

- **No flicker** — Textual's `reactive` system triggers differential re-renders
- **Independent poll loops** — each collector runs in its own `asyncio.Task`
- **2x2 Grid** — cards auto-fill left→right, top→bottom via CSS Grid
- **Compact metrics** — 18-char labels to fit half-width cards in grid layout
- **Per-query caching** — Postgres custom queries have independent `poll_every` with in-memory TTL cache
- **Graceful degradation** — connection failures show red dot + error, never crash

## Web Dashboard

- Port **9860** (registered in port registry)
- FastAPI backend reuses same collectors and config as TUI
- `GET /api/status` returns all server snapshots as JSON (includes `web_url`, `had_error` per server)
- `POST /api/clear-warnings` clears sticky yellow warning state
- Self-contained `static/index.html` — no npm, no build step
- `static/help.html` — usage guide linked from toolbar
- Dark/light theme, selectable 1/2/3 column grid layout, command palette (Ctrl+P)
- Server cards show clickable web app links when `web_url` is configured
- Frontend polls `/api/status` every 3 seconds

## Cross-Project Integration

This dashboard monitors servers from other projects. When those projects change:

| Change | Action |
|--------|--------|
| Engine port changes from 9847 | Update `config/servers.yaml` metrics_endpoint URL |
| Nagzerver port changes from 9800 | Update `config/servers.yaml` metrics_endpoint URL |
| Engine adds new `/metrics` fields | No action — new metrics auto-display |
| Redis moves to non-default port | Update `config/servers.yaml` redis host/port |
| Postgres DSN changes | Update `config/servers.yaml` postgres dsn |
| OBO database schema changes | Update custom queries in `config/servers.yaml` OBO Decks section |

## Deployment
- **Live URL:** https://bd-server-monitor.fly.dev
- Deployed via `~/Flyz/scripts/deploy.sh server-monitor`
- Production config at `~/Flyz/apps/server-monitor/config/servers.yaml` (polls Fly.io URLs instead of localhost)

## Documentation

| File | Purpose |
|------|---------|
| `README.md` | Full user-facing docs: setup, config, architecture |
| `METRICS_SPEC.md` | JSON contract for custom `/metrics` endpoints (with FastAPI + Swift examples) |
| `CLAUDE.md` | This file — project context for Claude |

