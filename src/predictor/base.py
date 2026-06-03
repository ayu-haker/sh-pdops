from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from datetime import datetime, timezone

from src.common.types import MetricPoint, PredictionResult


class MetricPredictor(ABC):
    def __init__(self, name: str = "base_predictor"):
        self.name = name
        self._predictions: List[PredictionResult] = []

    @abstractmethod
    async def predict(
        self, metrics: List[MetricPoint]
    ) -> List[PredictionResult]:
        pass

    def get_recent_predictions(self, n: int = 10) -> List[PredictionResult]:
        return sorted(
            self._predictions, key=lambda p: p.timestamp, reverse=True
        )[:n]

    def get_failure_predictions(
        self, threshold: float = 0.5
    ) -> List[PredictionResult]:
        return [
            p for p in self._predictions
            if p.failure_probability >= threshold
        ]
