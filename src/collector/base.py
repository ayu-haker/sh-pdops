from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime, timedelta, timezone

from src.common.types import MetricPoint, MetricType


class MetricCollector(ABC):
    def __init__(self, name: str = "base"):
        self.name = name
        self._buffer: List[MetricPoint] = []
        self._max_buffer_size = 10000

    @abstractmethod
    async def collect(self) -> List[MetricPoint]:
        pass

    def add_to_buffer(self, points: List[MetricPoint]) -> None:
        self._buffer.extend(points)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        self._buffer = [
            p for p in self._buffer if p.timestamp > cutoff
        ]
        if len(self._buffer) > self._max_buffer_size:
            self._buffer = self._buffer[-self._max_buffer_size:]

    def get_buffered(self, minutes: int = 5) -> List[MetricPoint]:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        return [p for p in self._buffer if p.timestamp > cutoff]

    def clear_buffer(self) -> None:
        self._buffer.clear()

    def make_point(
        self,
        name: str,
        value: float,
        type: MetricType,
        labels: Optional[dict] = None,
    ) -> MetricPoint:
        return MetricPoint(
            timestamp=datetime.now(timezone.utc),
            name=name,
            value=value,
            type=type,
            labels=labels or {},
            source=self.name,
        )
