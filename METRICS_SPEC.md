# Metrics Endpoint Spec v1.0

Every monitored custom server exposes `GET /metrics` returning the JSON format below. This is the contract between your servers and the server-monitor dashboard.

## Response Format

```json
{
  "metrics": [
    {
      "key": "requests_per_second",
      "label": "RPS",
      "value": 42.5,
      "unit": "req/s",
      "warn_above": 1000,
      "warn_below": null,
      "sparkline_history": [38, 40, 41, 42]
    }
  ]
}
```

## Fields

### `metrics[]` (required, array of metric objects)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `key` | string | yes | Machine-readable identifier (snake_case) |
| `label` | string | yes | Human-readable display label |
| `value` | number or string | yes | Current value |
| `unit` | string | no | Unit suffix for display (e.g. `"MB"`, `"req/s"`, `"%"`, `"count"`) |
| `warn_above` | number | no | Value above which to show warning (red) color |
| `warn_below` | number | no | Value below which to show warning (red) color |
| `sparkline_history` | number[] | no | Recent historical values for mini sparkline chart (newest last, max 60 points) |

## Color Logic

Colors are computed automatically from warn thresholds:
1. If `warn_above` is set and `value > warn_above` -> **red**
2. If `warn_below` is set and `value < warn_below` -> **red**
3. Otherwise -> **green**

## Example Payloads

### Scalar metrics (most common)

```json
{
  "metrics": [
    {"key": "uptime", "label": "Uptime", "value": 86400, "unit": "seconds"},
    {"key": "memory_rss", "label": "Memory (RSS)", "value": 128.5, "unit": "MB", "warn_above": 512},
    {"key": "rps", "label": "Requests/sec", "value": 42.5, "unit": "req/s", "sparkline_history": [38, 40, 41, 42]}
  ]
}
```

### Multi-field with thresholds

```json
{
  "metrics": [
    {"key": "open_tasks", "label": "Open Tasks", "value": 42, "unit": "tasks", "warn_above": 100},
    {"key": "error_rate", "label": "Error Rate", "value": 0.02, "unit": "%", "warn_above": 5},
    {"key": "cache_hit_rate", "label": "Cache Hit Rate", "value": 99.7, "unit": "%", "warn_below": 95},
    {"key": "queue_depth", "label": "Queue Depth", "value": 0, "unit": "jobs"}
  ]
}
```

### Text and status values

```json
{
  "metrics": [
    {"key": "daemon_state", "label": "State", "value": "running"},
    {"key": "role", "label": "Role", "value": "primary"},
    {"key": "version", "label": "Version", "value": "2.1.0"}
  ]
}
```

### Error response

When a server can't gather metrics, return an empty array:

```json
{
  "metrics": []
}
```

## Built-in Collectors (no /metrics endpoint needed)

For standard services, the dashboard polls natively:

| Service | Connection | Metrics Source |
|---------|-----------|----------------|
| Redis | `host` + `port` | `INFO` command (parsed by redis-py) |
| PostgreSQL | `dsn` string | `pg_stat_*` system views + custom YAML queries |

## Dashboard YAML Config

```yaml
servers:
  - name: "My API"
    type: http
    metrics_endpoint: "http://host:port/metrics"
    poll_every: 5

  - name: "Redis"
    type: redis
    host: "localhost"
    port: 6379
    poll_every: 10

  - name: "Postgres"
    type: postgres
    dsn: "postgresql://user:pass@host/db"
    system_stats: true
    poll_every: 15
    queries:
      - label: "Pending Jobs"
        sql: "SELECT COUNT(*) as value FROM jobs WHERE status = 'pending'"
        color: yellow
        warn_above: 100
        poll_every: 30
```

## Adding a /metrics Endpoint to Your Server

### FastAPI

```python
import os, time, psutil
from fastapi import APIRouter

router = APIRouter()
_start = time.time()

@router.get("/metrics")
async def metrics():
    proc = psutil.Process(os.getpid())
    return {
        "metrics": [
            {"key": "uptime", "label": "Uptime", "value": int(time.time() - _start), "unit": "seconds"},
            {"key": "memory_rss", "label": "Memory", "value": round(proc.memory_info().rss / 1048576, 1), "unit": "MB"},
            # add your app-specific metrics here
        ]
    }
```

### Swift (NIO)

Add a case to your HTTP handler's route switch:

```swift
case (.GET, "/metrics"):
    let metrics: [[String: Any]] = [
        ["key": "uptime", "label": "Uptime", "value": uptimeSeconds, "unit": "seconds"],
        ["key": "questions", "label": "Questions", "value": questionCount, "unit": "count"],
    ]
    return (200, ["metrics": metrics])
```
