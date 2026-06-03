from pydantic import BaseModel
from typing import Any, Dict, List, Optional


class HealthResponse(BaseModel):
    status: str
    uptime: float
    version: str
    healer_mode: str
    healer_type: str
    run_mode: str
    metrics_collected: int
    anomalies_active: int
    predictions_made: int
    actions_total: int
    health_score: float


class AnomalyResponse(BaseModel):
    id: str
    timestamp: str
    metric_name: str
    metric_value: float
    anomaly_type: str
    severity: str
    score: float
    description: str
    source: str
    labels: Dict[str, str]
    resolved: bool


class PredictionResponse(BaseModel):
    timestamp: str
    metric_name: str
    current_value: float
    predicted_value: float
    upper_bound: float
    lower_bound: float
    failure_probability: float
    time_to_failure_minutes: Optional[float] = None
    confidence: float


class ActionResponse(BaseModel):
    id: str
    action_type: str
    risk: str
    target: str
    status: str
    playbook: str
    triggered_by: str
    triggered_at: str
    executed_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None


class ActionApproveRequest(BaseModel):
    action_id: str
    approved: bool


class FaultInjectRequest(BaseModel):
    fault_type: str
    duration_seconds: int = 30


class MetricsQueryParams(BaseModel):
    service: Optional[str] = None
    metric: Optional[str] = None
    minutes: int = 5


class SystemStats(BaseModel):
    total_metrics: int
    total_anomalies: int
    resolved_anomalies: int
    active_anomalies: int
    total_predictions: int
    total_actions: int
    successful_actions: int
    failed_actions: int
    success_rate: float
    anomaly_rate: float
    avg_failure_probability: float
