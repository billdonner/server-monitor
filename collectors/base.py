"""Base collector ABC — all collectors return a dict in METRICS_SPEC.md shape."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseCollector(ABC):
    """Abstract base for all metric collectors.

    Subclasses implement ``collect()`` which returns a dict matching::

        {
          "metrics": [
            {"key": "...", "label": "...", "value": 42, "unit": "ms", ...}
          ]
        }

    On failure, return ``{"metrics": [], "error": "reason"}``.
    """

    def __init__(self, name: str, poll_every: int = 5, url: str = "") -> None:
        self.name = name
        self.poll_every = poll_every
        self.url = url

    @abstractmethod
    async def collect(self) -> dict:
        """Fetch current metrics. Must not raise — return error key on failure."""
        ...
