import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from src.collector.simulator import SimulatedCollector
from src.detector.statistical import StatisticalDetector
from src.predictor.failure_prediction import FailurePredictor
from src.healer.playbooks import LocalRemediationEngine
from src.config.settings import settings, RunMode


class ShPdopsEngine:
    def __init__(self):
        self.run_mode = settings.run_mode
        self.collector = SimulatedCollector()
        self.detector = StatisticalDetector(
            sensitivity=settings.anomaly_sensitivity,
        )
        self.predictor = FailurePredictor(
            horizon_minutes=settings.prediction_horizon_minutes,
            forecast_periods=settings.forecast_periods,
            threshold=settings.failure_probability_threshold,
        )
        self.healer = LocalRemediationEngine(
            mode=settings.healer_mode.value,
            max_concurrent=settings.max_concurrent_actions,
        )
        self._running = False
        self._start_time: Optional[datetime] = None
        self._collection_interval = settings.collection_interval_seconds

    async def start(self) -> None:
        self._running = True
        self._start_time = datetime.now(timezone.utc)
        logging.info("SH-PDOPS engine started (mode: %s)", self.run_mode.value)

        while self._running:
            try:
                await self._tick()
                await asyncio.sleep(self._collection_interval)
            except Exception as e:
                logging.error("Engine tick error: %s", e)

    async def stop(self) -> None:
        self._running = False
        logging.info("SH-PDOPS engine stopped")

    async def _tick(self) -> None:
        # 1. Collect metrics
        metrics = await self.collector.collect()

        # 2. Detect anomalies
        anomalies = await self.detector.detect(metrics)
        if anomalies:
            logging.info(
                "Detected %d anomalies", len(anomalies)
            )

        # 3. Predict failures
        predictions = await self.predictor.predict(metrics)
        high_risk = [p for p in predictions if p.failure_probability >= settings.failure_probability_threshold]
        if high_risk:
            logging.info(
                "High-risk predictions: %d", len(high_risk)
            )

        # 4. Trigger remediation for anomalies
        for anomaly in anomalies:
            action = await self.healer.handle_anomaly(anomaly)
            if action and action.status == "running":
                action = await self.healer.execute(action)
                logging.info(
                    "Healing action %s: %s on %s -> %s",
                    action.id, action.action_type.value,
                    action.target, action.status,
                )

        # 5. Trigger predictive remediation
        for pred in high_risk:
            action = await self.healer.handle_prediction(pred)
            if action and action.status == "running":
                action = await self.healer.execute(action)
                logging.info(
                    "Predictive action %s: %s on %s -> %s",
                    action.id, action.action_type.value,
                    action.target, action.status,
                )

    @property
    def uptime(self) -> float:
        if self._start_time is None:
            return 0.0
        return (datetime.now(timezone.utc) - self._start_time).total_seconds()

    def get_state(self) -> dict:
        return {
            "engine": self,
            "collector": self.collector,
            "detector": self.detector,
            "predictor": self.predictor,
            "healer": self.healer,
            "start_time": self._start_time or datetime.now(timezone.utc),
            "version": settings.app_version,
            "run_mode": self.run_mode,
        }
