#!/usr/bin/env python3
"""Server Monitor — browser-based web dashboard.

Usage:
    python web.py                              # default config, port 9860
    python web.py -c myconfig.yaml --port 8080 # custom config and port
"""

from __future__ import annotations

import argparse
import asyncio
import socket
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

import yaml
import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from collectors import HttpCollector, RedisCollector, PostgresCollector
from collectors.base import BaseCollector
from collectors.postgres_collector import CustomQuery


# ---------------------------------------------------------------------------
# Config loader (mirrors monitor.py — imports avoided to dodge Textual dep)
# ---------------------------------------------------------------------------

def load_config(path: Path) -> list[BaseCollector]:
    """Parse servers.yaml and return a list of collectors."""
    with open(path) as f:
        config = yaml.safe_load(f)

    collectors: list[BaseCollector] = []
    for srv in config.get("servers", []):
        name = srv["name"]
        stype = srv.get("type", "http")
        poll = srv.get("poll_every", 5)

        if srv.get("web_url"):
            _web_urls[name] = srv["web_url"]

        if stype == "http":
            collectors.append(
                HttpCollector(
                    name=name,
                    metrics_endpoint=srv["metrics_endpoint"],
                    poll_every=poll,
                )
            )
        elif stype == "redis":
            collectors.append(
                RedisCollector(
                    name=name,
                    host=srv.get("host", "localhost"),
                    port=srv.get("port", 6379),
                    poll_every=poll,
                )
            )
        elif stype == "postgres":
            queries = [
                CustomQuery(
                    label=q["label"],
                    sql=q["sql"],
                    color=q.get("color"),
                    warn_above=q.get("warn_above"),
                    warn_below=q.get("warn_below"),
                    poll_every=q.get("poll_every", poll),
                )
                for q in srv.get("queries", [])
            ]
            collectors.append(
                PostgresCollector(
                    name=name,
                    dsn=srv["dsn"],
                    poll_every=poll,
                    system_stats=srv.get("system_stats", True),
                    queries=queries,
                )
            )
        else:
            print(f"Warning: unknown server type '{stype}' for '{name}', skipping")

    return collectors


# ---------------------------------------------------------------------------
# Shared state — latest snapshot per server
# ---------------------------------------------------------------------------

_state: dict[str, dict] = {}
_collectors: list[BaseCollector] = []
_web_urls: dict[str, str] = {}   # server name → web app URL
_tasks: list[asyncio.Task] = []
_start_time: float = time.time()
_total_polls: int = 0


def _get_lan_ip() -> str:
    """Best-effort LAN IP detection."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


_lan_ip: str = _get_lan_ip()


async def _poll_loop(collector: BaseCollector) -> None:
    """Background poll loop for a single collector."""
    while True:
        try:
            result = await collector.collect()
        except Exception as exc:
            result = {"metrics": [], "error": str(exc)}
        global _total_polls
        _total_polls += 1
        _state[collector.name] = {
            "name": collector.name,
            "url": collector.url,
            "web_url": _web_urls.get(collector.name),
            "poll_every": collector.poll_every,
            "last_updated": time.time(),
            "metrics": result.get("metrics", []),
            "error": result.get("error"),
        }
        await asyncio.sleep(collector.poll_every)


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start collector tasks on startup, cancel on shutdown."""
    for c in _collectors:
        _tasks.append(asyncio.create_task(_poll_loop(c)))
    yield
    for t in _tasks:
        t.cancel()


app = FastAPI(title="Server Monitor", lifespan=lifespan)


@app.get("/api/status")
async def api_status():
    """Return latest snapshot of all monitored servers."""
    servers = list(_state.values())
    return JSONResponse({"servers": servers, "timestamp": time.time(), "lan_ip": _lan_ip})


@app.get("/metrics")
async def metrics():
    """Self-monitoring endpoint — METRICS_SPEC.md format."""
    servers = list(_state.values())
    healthy = sum(1 for s in servers if s.get("metrics") and not s.get("error"))
    errored = sum(1 for s in servers if s.get("error"))
    uptime = int(time.time() - _start_time)

    return JSONResponse({
        "metrics": [
            {
                "key": "servers_monitored",
                "label": "Servers Monitored",
                "value": len(_collectors),
                "unit": "count",
            },
            {
                "key": "servers_healthy",
                "label": "Servers Healthy",
                "value": healthy,
                "unit": "count",
                "color": "green",
            },
            {
                "key": "servers_errored",
                "label": "Servers Errored",
                "value": errored,
                "unit": "count",
                "warn_above": 0,
            },
            {
                "key": "uptime",
                "label": "Uptime",
                "value": uptime,
                "unit": "s",
            },
            {
                "key": "total_polls",
                "label": "Total Polls",
                "value": _total_polls,
                "unit": "count",
            },
        ]
    })


# Mount advice app sub-application if available
try:
    from advice_app.main import create_app as create_advice_app
    advice = create_advice_app()
    app.mount("/advice", advice)
except ImportError:
    pass  # advice app not installed — skip

# Serve static files (index.html) at root
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Server Monitor — Web Dashboard")
    parser.add_argument(
        "-c", "--config",
        default=str(Path(__file__).parent / "config" / "servers.yaml"),
        help="Path to servers.yaml config file",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=9860, help="Port (default: 9860)")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        sys.exit(1)

    global _collectors
    _collectors = load_config(config_path)
    if not _collectors:
        print("No servers configured. Edit config/servers.yaml")
        sys.exit(1)

    print(f"Starting web dashboard on http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
