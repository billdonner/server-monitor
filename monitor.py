#!/usr/bin/env python3
"""Server Monitor — flicker-free terminal dashboard for heterogeneous servers.

Usage:
    python monitor.py                    # use default config/servers.yaml
    python monitor.py -c myconfig.yaml   # use custom config
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from collectors import HttpCollector, RedisCollector, PostgresCollector
from collectors.base import BaseCollector
from collectors.postgres_collector import CustomQuery
from ui.app import DashboardApp


def load_config(path: Path) -> list[BaseCollector]:
    """Parse servers.yaml and return a list of collectors."""
    with open(path) as f:
        config = yaml.safe_load(f)

    collectors: list[BaseCollector] = []
    for srv in config.get("servers", []):
        name = srv["name"]
        stype = srv.get("type", "http")
        poll = srv.get("poll_every", 5)

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


def main() -> None:
    parser = argparse.ArgumentParser(description="Server Monitor Dashboard")
    parser.add_argument(
        "-c", "--config",
        default=str(Path(__file__).parent / "config" / "servers.yaml"),
        help="Path to servers.yaml config file",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        sys.exit(1)

    collectors = load_config(config_path)
    if not collectors:
        print("No servers configured. Edit config/servers.yaml")
        sys.exit(1)

    app = DashboardApp(collectors)
    app.run()


if __name__ == "__main__":
    main()
