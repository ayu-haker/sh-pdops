from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime, timezone

from src.common.types import (
    AnomalyEvent,
    PredictionResult,
    RemediationAction,
    ActionType,
    ActionRisk,
)
from src.common.utils import generate_id


class RemediationEngine(ABC):
    def __init__(
        self,
        name: str = "healer",
        mode: str = "semi_auto",
        max_concurrent: int = 3,
    ):
        self.name = name
        self.mode = mode
        self.max_concurrent = max_concurrent
        self._actions: List[RemediationAction] = []
        self._action_count = 0

    def _get_running_count(self) -> int:
        return sum(1 for a in self._actions if a.status == "running")

    def can_take_action(self) -> bool:
        return self._get_running_count() < self.max_concurrent

    def create_action(
        self,
        action_type: ActionType,
        risk: ActionRisk,
        target: str,
        playbook: str,
        triggered_by: str,
        parameters: Optional[dict] = None,
    ) -> RemediationAction:
        action = RemediationAction(
            id=generate_id("act"),
            action_type=action_type,
            risk=risk,
            target=target,
            parameters=parameters or {},
            playbook=playbook,
            status="pending",
            triggered_by=triggered_by,
            triggered_at=datetime.now(timezone.utc),
        )

        if self.mode == "auto":
            action.approved = True
            action.status = "running"
        elif self.mode == "semi_auto" and risk in (ActionRisk.LOW, ActionRisk.MEDIUM):
            action.approved = True
            action.status = "running"
        else:
            action.status = "pending_approval"

        self._actions.append(action)
        self._action_count += 1
        return action

    @abstractmethod
    async def execute(self, action: RemediationAction) -> RemediationAction:
        pass

    @abstractmethod
    async def rollback(self, action: RemediationAction) -> bool:
        pass

    def approve_action(self, action_id: str) -> bool:
        for action in self._actions:
            if action.id == action_id and action.status == "pending_approval":
                action.approved = True
                action.status = "running"
                return True
        return False

    def reject_action(self, action_id: str) -> bool:
        for action in self._actions:
            if action.id == action_id and action.status == "pending_approval":
                action.status = "rejected"
                return True
        return False

    def get_pending_actions(self) -> List[RemediationAction]:
        return [a for a in self._actions if a.status == "pending_approval"]

    def get_recent_actions(self, n: int = 20) -> List[RemediationAction]:
        return sorted(
            self._actions, key=lambda a: a.triggered_at, reverse=True
        )[:n]

    def get_stats(self) -> dict:
        total = len(self._actions)
        success = sum(1 for a in self._actions if a.status == "completed" and a.error is None)
        failed = sum(1 for a in self._actions if a.status == "failed")
        pending = sum(1 for a in self._actions if a.status in ("pending", "pending_approval"))
        running = sum(1 for a in self._actions if a.status == "running")
        return {
            "total": total,
            "successful": success,
            "failed": failed,
            "pending": pending,
            "running": running,
            "success_rate": (success / total * 100) if total > 0 else 0,
        }
