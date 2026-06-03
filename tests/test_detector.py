import pytest
from src.detector.statistical import StatisticalDetector
from src.common.types import MetricPoint, MetricType, AnomalyType
from datetime import datetime, timezone


def _make_metric(name: str, value: float, **labels) -> MetricPoint:
    return MetricPoint(
        timestamp=datetime.now(timezone.utc),
        name=name,
        value=value,
        type=MetricType.CPU,
        labels=labels or {"service": "test"},
        source="test",
    )


@pytest.mark.asyncio
async def test_detector_no_anomaly_with_normal_data():
    detector = StatisticalDetector(sensitivity=3.0)
    metrics = [_make_metric("test_cpu", 50.0) for _ in range(20)]
    anomalies = await detector.detect(metrics)
    assert len(anomalies) == 0


@pytest.mark.asyncio
async def test_detector_detects_spike():
    detector = StatisticalDetector(sensitivity=2.0)
    normal = [_make_metric("test_cpu", 50.0) for _ in range(15)]
    await detector.detect(normal)
    spike = [_make_metric("test_cpu", 500.0)]
    anomalies = await detector.detect(spike)
    assert len(anomalies) >= 1
    assert anomalies[0].anomaly_type == AnomalyType.SPIKE


@pytest.mark.asyncio
async def test_detector_detects_drop():
    detector = StatisticalDetector(sensitivity=2.0)
    normal = [_make_metric("test_cpu", 100.0) for _ in range(15)]
    await detector.detect(normal)
    drop = [_make_metric("test_cpu", 1.0)]
    anomalies = await detector.detect(drop)
    assert len(anomalies) >= 1
    assert anomalies[0].anomaly_type == AnomalyType.DROP


@pytest.mark.asyncio
async def test_detector_resolve():
    detector = StatisticalDetector(sensitivity=2.0)
    normal = [_make_metric("test_cpu", 50.0) for _ in range(15)]
    await detector.detect(normal)
    spike = [_make_metric("test_cpu", 500.0)]
    anomalies = await detector.detect(spike)
    assert len(detector.get_active_anomalies()) >= 1

    detector.resolve_anomaly(anomalies[0].id)
    assert len(detector.get_active_anomalies()) == 0


@pytest.mark.asyncio
async def test_detector_needs_minimum_data():
    detector = StatisticalDetector(sensitivity=2.0)
    few = [_make_metric("test_cpu", 500.0) for _ in range(3)]
    anomalies = await detector.detect(few)
    assert len(anomalies) == 0
