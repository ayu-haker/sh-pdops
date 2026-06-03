from collections import defaultdict
from typing import Dict, List
from datetime import datetime, timezone

import numpy as np

from src.predictor.base import MetricPredictor
from src.common.types import MetricPoint, PredictionResult
from src.common.utils import generate_id


class FailurePredictor(MetricPredictor):
    def __init__(
        self,
        name: str = "failure_predictor",
        horizon_minutes: int = 30,
        forecast_periods: int = 12,
        threshold: float = 0.7,
    ):
        super().__init__(name)
        self.horizon_minutes = horizon_minutes
        self.forecast_periods = forecast_periods
        self.threshold = threshold
        self._history: Dict[str, List[float]] = defaultdict(list)
        self._timestamps: Dict[str, List[datetime]] = defaultdict(list)
        self._max_history = 500
        self._model_ready = False

    async def predict(self, metrics: List[MetricPoint]) -> List[PredictionResult]:
        results: List[PredictionResult] = []
        current_time = datetime.now(timezone.utc)

        for metric in metrics:
            self._history[metric.name].append(metric.value)
            self._timestamps[metric.name].append(current_time)

            if len(self._history[metric.name]) > self._max_history:
                self._history[metric.name].pop(0)
                self._timestamps[metric.name].pop(0)

            if len(self._history[metric.name]) < self.forecast_periods * 2:
                continue

            values = np.array(self._history[metric.name][-50:])
            if len(values) < 10:
                continue

            result = self._predict_metric(metric.name, values, current_time)
            results.append(result)
            self._predictions.append(result)

        if len(results) > 0:
            self._model_ready = True

        return results

    def _predict_metric(
        self,
        metric_name: str,
        values: np.ndarray,
        current_time: datetime,
    ) -> PredictionResult:
        n = len(values)
        x = np.arange(n)
        coeffs = np.polyfit(x, values, 2)
        trend = np.polyval(coeffs, x)

        residuals = values - trend
        std_residual = np.std(residuals) if np.std(residuals) > 0 else 0.001
        mean_residual = np.mean(residuals)

        future_x = np.arange(n, n + self.forecast_periods)
        future_values = np.polyval(coeffs, future_x)

        noise = np.random.normal(mean_residual, std_residual, self.forecast_periods)
        for i in range(self.forecast_periods):
            future_values[i] += noise[i] * (1 + i * 0.1)

        predicted = future_values[-1]

        # Compute bounds (wider over time)
        upper_bound = predicted + 2 * std_residual * (1 + 0.1 * self.forecast_periods)
        lower_bound = predicted - 2 * std_residual * (1 + 0.1 * self.forecast_periods)

        current_value = float(values[-1])

        # Failure probability
        error_rate_idx = [i for i, n in enumerate(self._history.keys()) if "error" in n]
        cpu_idx = [i for i, n in enumerate(self._history.keys()) if "cpu" in n]

        prob = 0.0
        reasons = []

        if "error" in metric_name.lower():
            slope = coeffs[1]
            if slope > 0:
                prob += min(0.5, slope * 0.1)
                reasons.append("error_rate_increasing")

        if "cpu" in metric_name.lower():
            if current_value > 85:
                prob += 0.3
                reasons.append("cpu_high")
            if predicted > 90:
                prob += 0.2
                reasons.append("cpu_predicted_critical")

        if "memory" in metric_name.lower():
            if current_value > 85:
                prob += 0.3
                reasons.append("memory_high")
            if predicted > 90:
                prob += 0.2
                reasons.append("memory_predicted_critical")

        if "latency" in metric_name.lower():
            if current_value > 300:
                prob += 0.25
                reasons.append("high_latency")
            slope = coeffs[1]
            if slope > 5:
                prob += 0.2
                reasons.append("latency_increasing")

        prob = min(1.0, prob + 0.1)

        time_to_failure = None
        if prob > 0.3:
            failure_time = current_time.timestamp() + (1 - prob) * self.horizon_minutes * 60 * 1.5
            time_to_failure = max(1.0, (failure_time - current_time.timestamp()) / 60)

        confidence = min(0.9, 0.3 + 0.6 * (len(values) / self._max_history))

        return PredictionResult(
            timestamp=current_time,
            metric_name=metric_name,
            current_value=round(current_value, 2),
            predicted_value=round(float(predicted), 2),
            upper_bound=round(float(upper_bound), 2),
            lower_bound=round(float(lower_bound), 2),
            failure_probability=round(prob, 4),
            time_to_failure_minutes=round(time_to_failure, 1) if time_to_failure else None,
            confidence=round(confidence, 4),
            feature_importance={"trend": round(float(coeffs[0]), 4)},
        )

    def is_ready(self) -> bool:
        return self._model_ready
