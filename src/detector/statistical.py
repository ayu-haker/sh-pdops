import statistics
from collections import defaultdict
from typing import Dict, List

import numpy as np

from src.common.types import (
    MetricPoint,
    AnomalyEvent,
    AnomalyType,
)
from src.detector.base import AnomalyDetector


class StatisticalDetector(AnomalyDetector):
    def __init__(self, name: str = "statistical", sensitivity: float = 2.5):
        super().__init__(name, sensitivity)
        self._history: Dict[str, List[float]] = defaultdict(list)
        self._max_history = 200

    async def detect(self, metrics: List[MetricPoint]) -> List[AnomalyEvent]:
        anomalies: List[AnomalyEvent] = []

        for metric in metrics:
            history = self._history[metric.name]
            history.append(metric.value)
            if len(history) > self._max_history:
                history.pop(0)

            if len(history) < 10:
                continue

            mean = statistics.mean(history[:-5]) if len(history) > 5 else statistics.mean(history)
            stdev = statistics.stdev(history[:-5]) if len(history) > 10 else 1.0

            if stdev < 0.001:
                stdev = 0.001

            z_score = abs(metric.value - mean) / stdev

            if z_score > self.sensitivity:
                score = min(1.0, (z_score - self.sensitivity) / 5.0)

                if metric.value > mean:
                    anomaly_type = AnomalyType.SPIKE
                else:
                    anomaly_type = AnomalyType.DROP

                anomaly = self._create_anomaly(
                    metric=metric,
                    anomaly_type=anomaly_type,
                    score=round(score, 4),
                    description=(
                        f"{anomaly_type.value} detected on {metric.name}: "
                        f"{metric.value:.2f} (mean={mean:.2f}, std={stdev:.2f}, z={z_score:.2f})"
                    ),
                )
                anomalies.append(anomaly)
                self._anomalies.append(anomaly)

        return anomalies
