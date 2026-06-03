import pytest
from src.predictor.failure_prediction import FailurePredictor
from src.common.types import MetricPoint, MetricType
from datetime import datetime, timezone


def _make_metric(name: str, value: float) -> MetricPoint:
    return MetricPoint(
        timestamp=datetime.now(timezone.utc),
        name=name,
        value=value,
        type=MetricType.CPU,
        labels={"service": "test"},
        source="test",
    )


@pytest.mark.asyncio
async def test_predictor_needs_enough_data():
    predictor = FailurePredictor(forecast_periods=5)
    metrics = [_make_metric("test_cpu", 50.0) for _ in range(5)]
    results = await predictor.predict(metrics)
    assert len(results) == 0


@pytest.mark.asyncio
async def test_predictor_returns_results():
    predictor = FailurePredictor(forecast_periods=5)
    metrics = [_make_metric("test_cpu", 50.0) for _ in range(30)]
    results = await predictor.predict(metrics)
    assert len(results) > 0
    assert all(r.predicted_value is not None for r in results)


@pytest.mark.asyncio
async def test_predictor_high_failure_probability():
    predictor = FailurePredictor(forecast_periods=5, threshold=0.7)
    metrics = [_make_metric("test_cpu", 95.0) for _ in range(30)]
    results = await predictor.predict(metrics)
    high_risk = [r for r in results if r.failure_probability > 0.5]
    assert len(high_risk) > 0


@pytest.mark.asyncio
async def test_predictor_low_failure_probability():
    predictor = FailurePredictor(forecast_periods=5)
    metrics = [_make_metric("test_cpu", 30.0) for _ in range(30)]
    results = await predictor.predict(metrics)
    high_risk = [r for r in results if r.failure_probability > 0.5]
    assert len(high_risk) == 0


@pytest.mark.asyncio
async def test_predictor_confidence():
    predictor = FailurePredictor()
    metrics = [_make_metric("test_cpu", 50.0) for _ in range(100)]
    results = await predictor.predict(metrics)
    assert all(r.confidence > 0 for r in results)
