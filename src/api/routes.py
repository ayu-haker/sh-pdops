import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

from src.api.schemas import (
    HealthResponse,
    AnomalyResponse,
    PredictionResponse,
    ActionResponse,
    ActionApproveRequest,
    FaultInjectRequest,
    MetricsQueryParams,
    SystemStats,
)
from src.common.types import AnomalyEvent, PredictionResult, RemediationAction
from src.common.utils import compute_health_score

router = APIRouter()


def _anomaly_to_response(a: AnomalyEvent) -> AnomalyResponse:
    return AnomalyResponse(
        id=a.id,
        timestamp=a.timestamp.isoformat(),
        metric_name=a.metric_name,
        metric_value=a.metric_value,
        anomaly_type=a.anomaly_type.value,
        severity=a.severity.value,
        score=a.score,
        description=a.description,
        source=a.source,
        labels=a.labels,
        resolved=a.resolved,
    )


def _prediction_to_response(p: PredictionResult) -> PredictionResponse:
    return PredictionResponse(
        timestamp=p.timestamp.isoformat(),
        metric_name=p.metric_name,
        current_value=p.current_value,
        predicted_value=p.predicted_value,
        upper_bound=p.upper_bound,
        lower_bound=p.lower_bound,
        failure_probability=p.failure_probability,
        time_to_failure_minutes=p.time_to_failure_minutes,
        confidence=p.confidence,
    )


def _action_to_response(a: RemediationAction) -> ActionResponse:
    return ActionResponse(
        id=a.id,
        action_type=a.action_type.value,
        risk=a.risk.value,
        target=a.target,
        status=a.status,
        playbook=a.playbook,
        triggered_by=a.triggered_by,
        triggered_at=a.triggered_at.isoformat(),
        executed_at=a.executed_at.isoformat() if a.executed_at else None,
        completed_at=a.completed_at.isoformat() if a.completed_at else None,
        result=a.result,
        error=a.error,
    )


def _register_routes(app_state):
    """Register routes that need access to application state."""

    @router.get("/health", response_model=HealthResponse)
    async def get_health():
        engine = app_state["engine"]
        collector = app_state["collector"]
        detector = app_state["detector"]
        predictor = app_state["predictor"]
        healer = app_state["healer"]
        start_time = app_state["start_time"]

        uptime = (datetime.now(timezone.utc) - start_time).total_seconds()

        metrics = {}
        for p in collector._buffer[-10:]:
            if "cpu" in p.name:
                metrics["cpu"] = p.value
            if "memory" in p.name:
                metrics["memory"] = p.value
            if "latency" in p.name:
                metrics["latency"] = p.value
            if "error" in p.name:
                metrics["error_rate"] = p.value

        health_score = compute_health_score(metrics)
        healer_stats = healer.get_stats()

        return HealthResponse(
            status="healthy" if health_score > 60 else "degraded",
            uptime=uptime,
            version=app_state.get("version", "1.0.0"),
            healer_mode=healer.mode,
            healer_type="groq_ai" if "GroqHealer" in type(healer).__name__ else "local",
            run_mode=engine.run_mode.value if hasattr(engine, "run_mode") else "unknown",
            metrics_collected=len(collector._buffer),
            anomalies_active=len(detector.get_active_anomalies()),
            predictions_made=len(predictor._predictions),
            actions_total=healer_stats["total"],
            health_score=round(health_score, 1),
        )

    @router.get("/metrics", response_model=List[dict])
    async def get_metrics(service: Optional[str] = None, minutes: int = 5):
        collector = app_state["collector"]
        points = collector.get_buffered(minutes=minutes)

        if service:
            points = [p for p in points if p.labels.get("service") == service]

        return [
            {
                "timestamp": p.timestamp.isoformat(),
                "name": p.name,
                "value": p.value,
                "type": p.type.value,
                "labels": p.labels,
            }
            for p in points[-200:]
        ]

    @router.get("/anomalies", response_model=List[AnomalyResponse])
    async def get_anomalies(active_only: bool = False):
        detector = app_state["detector"]
        if active_only:
            anomalies = detector.get_active_anomalies()
        else:
            anomalies = detector._anomalies[-100:]
        return [_anomaly_to_response(a) for a in anomalies]

    @router.get("/predictions", response_model=List[PredictionResponse])
    async def get_predictions(high_risk_only: bool = False):
        predictor = app_state["predictor"]
        if high_risk_only:
            preds = predictor.get_failure_predictions(threshold=0.5)
        else:
            preds = predictor.get_recent_predictions(50)
        return [_prediction_to_response(p) for p in preds]

    @router.get("/actions", response_model=List[ActionResponse])
    async def get_actions(pending_only: bool = False):
        healer = app_state["healer"]
        if pending_only:
            actions = healer.get_pending_actions()
        else:
            actions = healer.get_recent_actions(50)
        return [_action_to_response(a) for a in actions]

    @router.post("/actions/approve")
    async def approve_action(req: ActionApproveRequest):
        healer = app_state["healer"]
        if req.approved:
            if healer.approve_action(req.action_id):
                return {"status": "approved", "action_id": req.action_id}
        else:
            if healer.reject_action(req.action_id):
                return {"status": "rejected", "action_id": req.action_id}
        raise HTTPException(404, "Action not found or not pending")

    @router.post("/simulate/fault")
    async def inject_fault(req: FaultInjectRequest):
        collector = app_state["collector"]
        if hasattr(collector, "enable_fault"):
            collector.enable_fault(fault_type=req.fault_type)
            return {
                "status": "fault_injected",
                "fault_type": req.fault_type,
                "duration": req.duration_seconds,
            }
        raise HTTPException(400, "Collector does not support fault injection")

    @router.post("/simulate/stop-fault")
    async def stop_fault():
        collector = app_state["collector"]
        if hasattr(collector, "disable_fault"):
            collector.disable_fault()
            return {"status": "fault_stopped"}
        raise HTTPException(400, "Collector does not support fault injection")

    @router.get("/stats", response_model=SystemStats)
    async def get_stats():
        detector = app_state["detector"]
        predictor = app_state["predictor"]
        healer = app_state["healer"]

        all_anomalies = detector._anomalies
        all_predictions = predictor._predictions
        healer_stats = healer.get_stats()

        total_anomalies = len(all_anomalies)
        resolved = sum(1 for a in all_anomalies if a.resolved)
        active = total_anomalies - resolved

        avg_failure_prob = 0.0
        if all_predictions:
            avg_failure_prob = (
                sum(p.failure_probability for p in all_predictions) / len(all_predictions)
            )

        return SystemStats(
            total_metrics=len(app_state["collector"]._buffer),
            total_anomalies=total_anomalies,
            resolved_anomalies=resolved,
            active_anomalies=active,
            total_predictions=len(all_predictions),
            total_actions=healer_stats["total"],
            successful_actions=healer_stats["successful"],
            failed_actions=healer_stats["failed"],
            success_rate=healer_stats["success_rate"],
            anomaly_rate=(total_anomalies / max(len(all_predictions), 1)) * 100,
            avg_failure_probability=round(avg_failure_prob * 100, 2),
        )

    @router.get("/healer/info")
    async def get_healer_info():
        healer = app_state["healer"]
        info: Dict[str, Any] = {
            "type": "groq_ai" if "GroqHealer" in type(healer).__name__ else "local",
            "mode": healer.mode,
            "stats": healer.get_stats(),
        }
        if "GroqHealer" in type(healer).__name__:
            info["model"] = healer.model
            info["has_api_key"] = bool(healer.api_key)
            info["fallback_to_local"] = healer.fallback_to_local
        return info

    router.websocket("/ws/metrics")
    async def metrics_websocket(websocket):
        await websocket.accept()
        try:
            while True:
                collector = app_state["collector"]
                points = collector.get_buffered(minutes=1)
                data = [
                    {"name": p.name, "value": p.value, "timestamp": p.timestamp.isoformat()}
                    for p in points[-50:]
                ]
                await websocket.send_json(data)
                await asyncio.sleep(2)
        except Exception:
            pass

    return router
