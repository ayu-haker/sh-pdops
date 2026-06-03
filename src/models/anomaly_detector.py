import numpy as np
from sklearn.ensemble import IsolationForest
from typing import List, Tuple
import joblib
from pathlib import Path


class MLAnomalyDetector:
    def __init__(self, contamination: float = 0.05, random_state: int = 42):
        self.contamination = contamination
        self.model = IsolationForest(
            contamination=contamination,
            random_state=random_state,
            n_estimators=100,
            max_samples="auto",
        )
        self._trained = False

    def _extract_features(self, values: np.ndarray) -> np.ndarray:
        if len(values) < 10:
            return np.zeros((1, 5))

        features = []
        window = 10
        for i in range(len(values) - window + 1):
            segment = values[i : i + window]
            feat = np.array([
                np.mean(segment),
                np.std(segment),
                np.max(segment),
                np.min(segment),
                segment[-1] - segment[0],
            ])
            features.append(feat)

        if len(features) > 30:
            features = features[-30:]

        return np.array(features) if features else np.zeros((1, 5))

    def train(self, values: np.ndarray) -> None:
        features = self._extract_features(values)
        if features.shape[0] < 5:
            return
        self.model.fit(features)
        self._trained = True

    def predict(self, values: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        features = self._extract_features(values)
        if features.shape[0] == 0:
            return np.array([1]), np.array([0.0])

        preds = self.model.predict(features)
        scores = self.model.score_samples(features)

        # -1 = anomaly, 1 = normal -> anomaly score
        anomaly_scores = np.where(preds == -1, 1, 0)
        confidence = 1 - np.abs(scores) / np.max(np.abs(scores) + 1e-8)

        return anomaly_scores, confidence

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.model, path)

    def load(self, path: Path) -> None:
        self.model = joblib.load(path)
        self._trained = True

    @property
    def is_trained(self) -> bool:
        return self._trained
