"""Base collector ABC and shared data types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class MetricItem:
    key: str
    label: str
    value: float | int | str
    unit: str = ""
    color: str | None = None
    warn_above: float | None = None
    warn_below: float | None = None
    sparkline: list[float] = field(default_factory=list)

    @property
    def display_color(self) -> str:
        """Compute effective color from thresholds."""
        if self.color:
            return self.color
        if isinstance(self.value, (int, float)):
            if self.warn_above is not None and self.value > self.warn_above:
                return "red"
            if self.warn_below is not None and self.value < self.warn_below:
                return "red"
        return "green"

    @property
    def display_value(self) -> str:
        if isinstance(self.value, float):
            return f"{self.value:,.1f}"
        if isinstance(self.value, int):
            return f"{self.value:,}"
        return str(self.value)


@dataclass
class ServerInfo:
    name: str
    version: str = ""
    uptime_seconds: int = 0


@dataclass
class CollectorResult:
    server: ServerInfo
    metrics: list[MetricItem]
    error: str | None = None
    reachable: bool = True


class BaseCollector(ABC):
    """Abstract base for all metric collectors."""

    def __init__(self, name: str, poll_every: int = 5) -> None:
        self.name = name
        self.poll_every = poll_every

    @abstractmethod
    async def collect(self) -> CollectorResult:
        """Fetch current metrics. Must not raise — return error in result."""
        ...
