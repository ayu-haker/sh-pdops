from pydantic import BaseModel, Field
from typing import Optional, Any, Dict, List
from enum import Enum
from datetime import datetime


class MetricType(str, Enum):
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    LATENCY = "latency"
    ERROR_RATE = "error_rate"
    REQUEST_RATE = "request_rate"
    CUSTOM = "custom"


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    FATAL = "fatal"


class AnomalyType(str, Enum):
    SPIKE = "spike"
    DROP = "drop"
    TREND_CHANGE = "trend_change"
    SEASONAL_BREAK = "seasonal_break"
    CORRELATION_BREAK = "correlation_break"
    UNKNOWN = "unknown"


class ActionType(str, Enum):
    RESTART = "restart"
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    ROLLBACK = "rollback"
    DNS_FAILOVER = "dns_failover"
    CLEAR_CACHE = "clear_cache"
    KILL_PROCESS = "kill_process"
    RUN_SCRIPT = "run_script"
    CUSTOM = "custom"


class ActionRisk(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class MetricPoint(BaseModel):
    timestamp: datetime
    name: str
    value: float
    type: MetricType
    labels: Dict[str, str] = {}
    source: str = "unknown"


class AnomalyEvent(BaseModel):
    id: str
    timestamp: datetime
    metric_name: str
    metric_value: float
    anomaly_type: AnomalyType
    severity: Severity
    score: float = Field(ge=0.0, le=1.0)
    description: str
    source: str
    labels: Dict[str, str] = {}
    resolved: bool = False
    resolved_at: Optional[datetime] = None


class PredictionResult(BaseModel):
    timestamp: datetime
    metric_name: str
    current_value: float
    predicted_value: float
    upper_bound: float
    lower_bound: float
    failure_probability: float = Field(ge=0.0, le=1.0)
    time_to_failure_minutes: Optional[float] = None
    confidence: float = Field(ge=0.0, le=1.0)
    feature_importance: Dict[str, float] = {}


class RemediationAction(BaseModel):
    id: str
    action_type: ActionType
    risk: ActionRisk
    target: str
    parameters: Dict[str, Any] = {}
    playbook: str
    status: str = "pending"
    triggered_by: str
    triggered_at: datetime
    executed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[str] = None
    error: Optional[str] = None
    approved: bool = False
    approved_by: Optional[str] = None


class Playbook(BaseModel):
    name: str
    description: str
    action_type: ActionType
    risk: ActionRisk
    conditions: Dict[str, Any]
    steps: List[Dict[str, Any]]
    timeout_seconds: int = 60
    rollback_steps: List[Dict[str, Any]] = []


class SystemHealth(BaseModel):
    status: str
    total_metrics: int
    anomalies_detected: int
    anomalies_resolved: int
    predictions_made: int
    actions_taken: int
    actions_successful: int
    actions_failed: int
    uptime_seconds: float
    last_update: datetime
