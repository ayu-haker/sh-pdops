import asyncio
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.common.types import (
    ActionType,
    ActionRisk,
    AnomalyEvent,
    PredictionResult,
    Playbook,
    RemediationAction,
)
from src.common.utils import load_yaml
from src.healer.base import RemediationEngine


class PlaybookManager:
    def __init__(self, playbooks_dir: Optional[Path] = None):
        self.playbooks_dir = playbooks_dir or Path("playbooks")
        self._playbooks: Dict[str, Playbook] = {}
        self._load_playbooks()

    def _load_playbooks(self) -> None:
        if not self.playbooks_dir.exists():
            return
        for filepath in self.playbooks_dir.glob("*.yaml"):
            data = load_yaml(filepath)
            playbook = Playbook(**data)
            self._playbooks[playbook.name] = playbook

    def register(self, playbook: Playbook) -> None:
        self._playbooks[playbook.name] = playbook

    def get(self, name: str) -> Optional[Playbook]:
        return self._playbooks.get(name)

    def find_for_anomaly(self, metric_name: str, severity: str) -> Optional[Playbook]:
        metric_lower = metric_name.lower()
        for pb in self._playbooks.values():
            cond = pb.conditions
            if "metric_pattern" in cond and cond["metric_pattern"] in metric_lower:
                if "min_severity" in cond:
                    severities = {"info": 0, "warning": 1, "critical": 2, "fatal": 3}
                    if severities.get(severity, 0) < severities.get(cond["min_severity"], 0):
                        continue
                return pb
        return None

    def list_playbooks(self) -> List[Playbook]:
        return list(self._playbooks.values())


class LocalRemediationEngine(RemediationEngine):
    def __init__(
        self,
        name: str = "local_healer",
        mode: str = "semi_auto",
        max_concurrent: int = 3,
    ):
        super().__init__(name, mode, max_concurrent)
        self.playbooks = PlaybookManager()

    async def execute(self, action: RemediationAction) -> RemediationAction:
        action.executed_at = datetime.now(timezone.utc)
        action.status = "running"

        await asyncio.sleep(random.uniform(0.5, 1.5))

        # Simulate execution outcome
        success_prob = 0.85
        if random.random() < success_prob:
            action.status = "completed"
            action.result = f"Successfully executed {action.action_type.value} on {action.target}"
        else:
            action.status = "failed"
            action.error = f"Failed to execute {action.action_type.value}: simulated timeout"

        action.completed_at = datetime.now(timezone.utc)
        return action

    async def rollback(self, action: RemediationAction) -> bool:
        await asyncio.sleep(random.uniform(0.3, 1.0))
        return random.random() < 0.9

    async def handle_anomaly(self, anomaly: AnomalyEvent) -> Optional[RemediationAction]:
        playbook = self.playbooks.find_for_anomaly(anomaly.metric_name, anomaly.severity.value)
        if playbook is None:
            return None

        target = anomaly.labels.get("service", anomaly.metric_name)
        action = self.create_action(
            action_type=playbook.action_type,
            risk=playbook.risk,
            target=target,
            playbook=playbook.name,
            triggered_by=f"anomaly:{anomaly.id}",
        )
        return action

    async def handle_prediction(
        self, prediction: PredictionResult
    ) -> Optional[RemediationAction]:
        if prediction.failure_probability < 0.7:
            return None

        metric_name = prediction.metric_name
        action_type = ActionType.SCALE_UP
        risk = ActionRisk.MEDIUM
        target = metric_name.split("_")[0] if "_" in metric_name else metric_name
        playbook_name = "predictive_scale_up"

        if prediction.failure_probability > 0.9:
            risk = ActionRisk.HIGH

        action = self.create_action(
            action_type=action_type,
            risk=risk,
            target=target,
            playbook=playbook_name,
            triggered_by=f"prediction:{prediction.metric_name}",
            parameters={
                "failure_probability": prediction.failure_probability,
                "predicted_value": prediction.predicted_value,
                "time_to_failure": prediction.time_to_failure_minutes,
            },
        )
        return action
