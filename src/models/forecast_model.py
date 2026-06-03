import numpy as np
from typing import Tuple, Optional
from pathlib import Path
import joblib


class ForecastModel:
    def __init__(self, forecast_periods: int = 12):
        self.forecast_periods = forecast_periods
        self._coefficients: Optional[np.ndarray] = None
        self._residual_std: float = 1.0
        self._trained = False

    def train(self, values: np.ndarray) -> None:
        if len(values) < 5:
            return

        degree = min(3, len(values) - 1)
        x = np.arange(len(values))
        self._coefficients = np.polyfit(x, values, degree)

        trend = np.polyval(self._coefficients, x)
        residuals = values - trend
        self._residual_std = np.std(residuals) if np.std(residuals) > 0 else 0.001

        self._trained = True

    def forecast(self, values: np.ndarray) -> Tuple[float, float, float]:
        if not self._trained:
            return float(values[-1]), float(values[-1]), float(values[-1])

        n = len(values)
        future_x = np.arange(n, n + self.forecast_periods)
        predicted = np.polyval(self._coefficients, future_x)

        # Add uncertainty bands
        std_scale = 1 + 0.05 * self.forecast_periods
        final_pred = float(predicted[-1])
        upper = float(predicted[-1] + 2 * self._residual_std * std_scale)
        lower = float(predicted[-1] - 2 * self._residual_std * std_scale)

        return final_pred, upper, lower

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "coefficients": self._coefficients,
                "residual_std": self._residual_std,
                "forecast_periods": self.forecast_periods,
            },
            path,
        )

    def load(self, path: Path) -> None:
        data = joblib.load(path)
        self._coefficients = data["coefficients"]
        self._residual_std = data["residual_std"]
        self.forecast_periods = data["forecast_periods"]
        self._trained = True

    @property
    def is_trained(self) -> bool:
        return self._trained
