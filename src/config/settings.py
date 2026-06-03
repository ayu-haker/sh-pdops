import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from enum import Enum


class RunMode(str, Enum):
    SIMULATION = "simulation"
    LIVE = "live"
    HYBRID = "hybrid"


class HealerMode(str, Enum):
    AUTO = "auto"
    MANUAL = "manual"
    SEMI_AUTO = "semi_auto"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "SH-PDOPS"
    app_version: str = "1.0.0"
    debug: bool = True

    run_mode: RunMode = RunMode.SIMULATION
    healer_mode: HealerMode = HealerMode.SEMI_AUTO

    collection_interval_seconds: int = 15
    metrics_retention_hours: int = 24
    max_metrics_points: int = 10000

    anomaly_sensitivity: float = 2.5
    detection_window_minutes: int = 5
    rule_check_interval_seconds: int = 30

    prediction_horizon_minutes: int = 30
    forecast_periods: int = 12
    model_retrain_interval_hours: int = 24
    failure_probability_threshold: float = 0.7

    max_concurrent_actions: int = 3
    action_timeout_seconds: int = 60
    auto_heal_low_risk: bool = True
    require_approval_high_risk: bool = True

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 1

    dashboard_port: int = 8501

    database_url: str = "sqlite:///data/sh-pdops.db"
    redis_url: Optional[str] = None

    prometheus_url: Optional[str] = None
    k8s_config_path: Optional[str] = None

    anomaly_model_path: str = "data/models/anomaly_detector.joblib"
    failure_model_path: str = "data/models/failure_predictor.joblib"
    forecast_model_path: str = "data/models/forecast_model.joblib"

    groq_api_key: Optional[str] = None
    groq_model: str = "llama3-8b-8192"
    healer_type: str = "auto"


settings = Settings()

# Railway injects PORT env var — override api_port if present
_railway_port = os.environ.get("PORT")
if _railway_port:
    try:
        settings.api_port = int(_railway_port)
    except (ValueError, TypeError):
        pass

# In Railway, dashboard runs as a separate service
_railway_dashboard_port = os.environ.get("DASHBOARD_PORT")
if _railway_dashboard_port:
    try:
        settings.dashboard_port = int(_railway_dashboard_port)
    except (ValueError, TypeError):
        pass
