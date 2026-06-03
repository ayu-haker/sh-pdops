import numpy as np
from sklearn.ensemble import RandomForestRegressor
from typing import List, Tuple, Optional
from pathlib import Path
import joblib


class MLFailurePredictor:
    def __init__(self, random_state: int = 42):
        self.model = RandomForestRegressor(
            n_estimators=50,
            max_depth=10,
            random_state=random_state,
            n_jobs=-1,
        )
        self._trained = False
        self._feature_names: List[str] = []

    def _build_features(self, values: np.ndarray) -> np.ndarray:
        if len(values) < 20:
            return np.zeros((1, 7))

        features = []
        for i in range(10, len(values)):
            window = values[i - 10 : i]
            feat = [
                np.mean(window),
                np.std(window),
                np.max(window),
                np.min(window),
                window[-1],
                window[-1] - window[0],
                np.polyfit(np.arange(len(window)), window, 1)[0],
            ]
            features.append(feat)

        self._feature_names = [
            "mean", "std", "max", "min", "last", "diff", "slope",
        ]
        return np.array(features) if features else np.zeros((1, 7))

    def _create_labels(self, values: np.ndarray, horizon: int = 5) -> np.ndarray:
        labels = []
        for i in range(10, len(values) - horizon):
            future_idx = min(i + horizon, len(values) - 1)
            future_max = np.max(values[i:future_idx])
            threshold = np.mean(values) + 2 * np.std(values)
            labels.append(1.0 if future_max > threshold else 0.0)
        return np.array(labels) if labels else np.zeros(1)

    def train(self, values: np.ndarray) -> None:
        features = self._build_features(values)
        labels = self._create_labels(values)
        if features.shape[0] < 10 or len(labels) < 10:
            return
        if features.shape[0] > len(labels):
            features = features[: len(labels)]
        self.model.fit(features, labels)
        self._trained = True

    def predict_failure_probability(self, values: np.ndarray) -> float:
        features = self._build_features(values)
        if features.shape[0] == 0:
            return 0.0
        latest = features[-1:]

        if not self._trained:
            return 0.0

        prob = self.model.predict(latest)[0]
        return float(np.clip(prob, 0.0, 1.0))

    def predict_with_confidence(self, values: np.ndarray) -> Tuple[float, float]:
        features = self._build_features(values)
        if features.shape[0] == 0 or not self._trained:
            return 0.0, 0.0

        latest = features[-1:]
        preds = []
        for estimator in self.model.estimators_:
            preds.append(estimator.predict(latest)[0])

        mean_prob = float(np.mean(preds))
        std_prob = float(np.std(preds))
        confidence = float(np.clip(1.0 - std_prob, 0.0, 1.0))
        return mean_prob, confidence

    def feature_importance(self) -> dict:
        if not self._trained:
            return {}
        return dict(zip(
            self._feature_names,
            [round(x, 4) for x in self.model.feature_importances_],
        ))

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"model": self.model, "features": self._feature_names}, path)

    def load(self, path: Path) -> None:
        data = joblib.load(path)
        self.model = data["model"]
        self._feature_names = data["features"]
        self._trained = True

    @property
    def is_trained(self) -> bool:
        return self._trained
