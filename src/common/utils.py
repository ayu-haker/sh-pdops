import uuid
import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict
import yaml
from pathlib import Path


def generate_id(prefix: str = "") -> str:
    uid = str(uuid.uuid4())[:8]
    return f"{prefix}_{uid}" if prefix else uid


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def load_yaml(path: Path) -> Dict[str, Any]:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def hash_dict(d: Dict[str, Any]) -> str:
    return hashlib.md5(json.dumps(d, sort_keys=True).encode()).hexdigest()[:12]


def compute_health_score(metrics: Dict[str, float]) -> float:
    weights = {
        "cpu": 0.25,
        "memory": 0.20,
        "disk": 0.15,
        "latency": 0.20,
        "error_rate": 0.20,
    }
    thresholds = {
        "cpu": 80.0,
        "memory": 80.0,
        "disk": 85.0,
        "latency": 200.0,
        "error_rate": 5.0,
    }
    score = 0.0
    total_weight = 0.0
    for key, value in metrics.items():
        if key in weights:
            threshold = thresholds.get(key, 100.0)
            health = max(0.0, 1.0 - (value / threshold))
            score += health * weights[key]
            total_weight += weights[key]
    return (score / total_weight * 100) if total_weight > 0 else 100.0
