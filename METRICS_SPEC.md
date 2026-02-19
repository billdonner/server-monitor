# Metrics Endpoint Spec v1.0

Every monitored server exposes `GET /metrics` (or equivalent) returning this JSON shape.

## Response Format

```json
{
  "server": {
    "name": "My Server",
    "version": "1.2.3",
    "uptime_seconds": 86400
  },
  "metrics": [
    {
      "key": "requests_per_second",
      "label": "RPS",
      "value": 42.5,
      "unit": "req/s",
      "type": "gauge",
      "color": "cyan",
      "warn_above": 1000,
      "warn_below": null,
      "sparkline": [38, 41, 42, 45, 42]
    }
  ]
}
```

## Fields

### `server` (required)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Human-readable server name |
| `version` | string | no | Server version string |
| `uptime_seconds` | number | yes | Seconds since server start |

### `metrics[]` (required, array of metric objects)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `key` | string | yes | Machine-readable identifier (snake_case) |
| `label` | string | yes | Human-readable display label |
| `value` | number or string | yes | Current value |
| `unit` | string | no | Unit suffix for display (e.g. "MB", "req/s", "%", "count") |
| `type` | string | no | Display hint: `gauge`, `counter`, `percentage`, `table`, `text`. Default: `gauge` |
| `color` | string | no | Display color: `red`, `green`, `yellow`, `cyan`, `magenta`, `blue`, `white`. Default: auto from warn thresholds |
| `warn_above` | number | no | Value above which to show warning color |
| `warn_below` | number | no | Value below which to show warning color |
| `sparkline` | number[] | no | Recent historical values for mini sparkline chart (newest last, max 60 points) |

## Value Types

- **gauge**: A point-in-time measurement (memory, connections, queue depth)
- **counter**: A monotonically increasing count (requests served, errors total)
- **percentage**: A 0-100 value displayed with `%` suffix
- **table**: `value` is an array of objects displayed as a mini table
- **text**: `value` is a string displayed as-is

## Color Logic

If `color` is not specified:
1. If `warn_above` is set and `value > warn_above` -> red
2. If `warn_below` is set and `value < warn_below` -> red
3. Otherwise -> green

## Built-in Collectors (no /metrics endpoint needed)

For standard services, the dashboard polls natively:

| Service | Connection | Metrics Source |
|---------|-----------|----------------|
| Redis | `redis://host:port` | `INFO` command (parsed by redis-py) |
| PostgreSQL | `postgresql://...` | `pg_stat_*` system views + custom YAML queries |

## Custom Server Integration

Drop a `/metrics` endpoint in your server conforming to this spec. Example for FastAPI:

```python
@router.get("/metrics")
async def metrics():
    return {
        "server": {"name": "My App", "uptime_seconds": int(time.time() - START)},
        "metrics": [
            {"key": "active_users", "label": "Active Users", "value": 42, "unit": "count"},
        ]
    }
```

## Dashboard YAML Config

```yaml
servers:
  - name: "Trivia Engine"
    type: http
    url: "http://127.0.0.1:9847/metrics"
    poll_every: 5

  - name: "Nagzerver"
    type: http
    url: "http://127.0.0.1:9800/api/v1/metrics"
    poll_every: 5

  - name: "Redis"
    type: redis
    url: "redis://localhost:6379"
    poll_every: 10

  - name: "Postgres (Nagz)"
    type: postgres
    dsn: "postgresql://nagz:nagz@localhost:5433/nagz"
    poll_every: 15
    queries:
      - label: "Open Nags"
        sql: "SELECT COUNT(*) as value FROM nags WHERE status = 'open'"
        color: yellow
        warn_above: 100
```
