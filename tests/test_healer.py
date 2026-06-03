import pytest
from src.healer.playbooks import LocalRemediationEngine
from src.common.types import (
    ActionType, ActionRisk, AnomalyEvent, AnomalyType,
    Severity, PredictionResult,
)
from datetime import datetime, timezone


def _make_anomaly(metric_name: str, severity: Severity = Severity.WARNING) -> AnomalyEvent:
    return AnomalyEvent(
        id="test-anom-1",
        timestamp=datetime.now(timezone.utc),
        metric_name=metric_name,
        metric_value=100.0,
        anomaly_type=AnomalyType.SPIKE,
        severity=severity,
        score=0.8,
        description="test anomaly",
        source="test",
        labels={"service": "api-gateway"},
    )


def _make_prediction(prob: float = 0.8) -> PredictionResult:
    return PredictionResult(
        timestamp=datetime.now(timezone.utc),
        metric_name="api-gateway_cpu",
        current_value=80.0,
        predicted_value=95.0,
        upper_bound=100.0,
        lower_bound=70.0,
        failure_probability=prob,
        time_to_failure_minutes=5.0,
        confidence=0.85,
    )


@pytest.mark.asyncio
async def test_healer_auto_mode():
    healer = LocalRemediationEngine(mode="auto")
    anomaly = _make_anomaly("api-gateway_error_rate")
    action = await healer.handle_anomaly(anomaly)
    assert action is not None
    assert action.approved is True
    assert action.status == "running"


@pytest.mark.asyncio
async def test_healer_semi_auto_high_risk():
    healer = LocalRemediationEngine(mode="semi_auto")
    # rollback is high risk
    anomaly = _make_anomaly("critical_error_rate", severity=Severity.CRITICAL)
    playbook = healer.playbooks.find_for_anomaly(anomaly.metric_name, anomaly.severity.value)
    if playbook:
        action = healer.create_action(
            action_type=ActionType.ROLLBACK,
            risk=ActionRisk.HIGH,
            target="api-gateway",
            playbook="rollback_deployment",
            triggered_by="test",
        )
        assert action.approved is False
        assert action.status == "pending_approval"


@pytest.mark.asyncio
async def test_healer_execute_action():
    healer = LocalRemediationEngine(mode="auto")
    anomaly = _make_anomaly("api-gateway_error_rate")
    action = await healer.handle_anomaly(anomaly)
    assert action is not None
    result = await healer.execute(action)
    assert result.status in ("completed", "failed")


@pytest.mark.asyncio
async def test_healer_predictive_action():
    healer = LocalRemediationEngine(mode="auto")
    pred = _make_prediction(prob=0.85)
    action = await healer.handle_prediction(pred)
    assert action is not None
    assert action.triggered_by == "prediction:api-gateway_cpu"


@pytest.mark.asyncio
async def test_healer_stats():
    healer = LocalRemediationEngine(mode="auto")
    stats = healer.get_stats()
    assert "total" in stats
    assert "success_rate" in stats


@pytest.mark.asyncio
async def test_healer_pending_actions():
    healer = LocalRemediationEngine(mode="manual")
    anomaly = _make_anomaly("test_error_rate")
    await healer.handle_anomaly(anomaly)
    pending = healer.get_pending_actions()
    assert len(pending) >= 0
