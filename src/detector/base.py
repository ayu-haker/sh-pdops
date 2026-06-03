from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime, timezone

from src.common.types import MetricPoint, AnomalyEvent, Severity, AnomalyType
from src.common.utils import generate_id


class AnomalyDetector(ABC):
    def __init__(self, name: str = "base_detector", sensitivity: float = 2.5):
        self.name = name
        self.sensitivity = sensitivity
        self._anomalies: List[AnomalyEvent] = []

    @abstractmethod
    async def detect(self, metrics: List[MetricPoint]) -> List[AnomalyEvent]:
        pass

    def _create_anomaly(
        self,
        metric: MetricPoint,
        anomaly_type: AnomalyType,
        score: float,
        description: str,
        severity: Optional[Severity] = None,
    ) -> AnomalyEvent:
        if severity is None:
            if score >= 0.9:
                severity = Severity.FATAL
            elif score >= 0.75:
                severity = Severity.CRITICAL
            elif score >= 0.5:
                severity = Severity.WARNING
            else:
                severity = Severity.INFO

        return AnomalyEvent(
            id=generate_id("anom"),
            timestamp=datetime.now(timezone.utc),
            metric_name=metric.name,
            metric_value=metric.value,
            anomaly_type=anomaly_type,
            severity=severity,
            score=score,
            description=description,
            source=self.name,
            labels=metric.labels,
        )

    def get_active_anomalies(self) -> List[AnomalyEvent]:
        return [a for a in self._anomalies if not a.resolved]

    def resolve_anomaly(self, anomaly_id: str) -> bool:
        for a in self._anomalies:
            if a.id == anomaly_id:
                a.resolved = True
                a.resolved_at = datetime.now(timezone.utc)
                return True
        return False

    def resolve_all(self) -> int:
        count = 0
        now = datetime.now(timezone.utc)
        for a in self._anomalies:
            if not a.resolved:
                a.resolved = True
                a.resolved_at = now
                count += 1
        return count
