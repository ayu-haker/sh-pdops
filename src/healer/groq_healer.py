import asyncio
import json
import logging
import random
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx

from src.common.types import (
    ActionType,
    ActionRisk,
    AnomalyEvent,
    PredictionResult,
    RemediationAction,
)
from src.healer.base import RemediationEngine
from src.healer.playbooks import LocalRemediationEngine

GROQ_API_BASE = "https://api.groq.com/openai/v1"

ANOMALY_SYSTEM_PROMPT = (
    "You are a senior DevOps SRE analyzing a system anomaly. "
    "Given the anomaly context, respond with a JSON object exactly in this format:\n\n"
    '{\n  "reasoning": "brief explanation",\n'
    '  "action_type": "restart|scale_up|scale_down|rollback|dns_failover|clear_cache|kill_process|run_script|custom",\n'
    '  "risk": "low|medium|high",\n'
    '  "target_service": "service name",\n'
    '  "playbook_name": "groq_ai_recommended"\n}\n\n'
    "Rules:\n"
    "- CPU/memory spikes: restart or scale_up\n"
    "- Latency bursts: restart or clear_cache\n"
    "- Error rate bursts: restart or rollback\n"
    "- Traffic surges: scale_up\n"
    "- Critical severity: use high risk\n"
    "- Warning severity: use medium risk\n"
    "- Info severity: use low risk or no action needed\n"
    "Respond with ONLY the JSON object, no markdown, no explanation."
)

PREDICTION_SYSTEM_PROMPT = (
    "You are a senior DevOps SRE analyzing a predictive failure alert. "
    "Given the prediction context, respond with a JSON object exactly in this format:\n\n"
    '{\n  "reasoning": "brief explanation",\n'
    '  "action_type": "restart|scale_up|scale_down|rollback|dns_failover|clear_cache|kill_process|run_script|custom",\n'
    '  "risk": "low|medium|high",\n'
    '  "target_service": "service name",\n'
    '  "playbook_name": "groq_ai_predictive"\n}\n\n'
    "Rules:\n"
    "- High failure probability (>0.9): high risk, proactive restart or scale_up\n"
    "- Medium probability (0.7-0.9): medium risk, scale_up or clear_cache\n"
    "- Low time to failure: higher risk action\n"
    "- Respond with ONLY the JSON object, no markdown, no explanation."
)


class GroqHealer(RemediationEngine):
    def __init__(
        self,
        api_key: str = "",
        model: str = "llama3-8b-8192",
        name: str = "groq_healer",
        mode: str = "semi_auto",
        max_concurrent: int = 3,
        fallback_to_local: bool = True,
    ):
        super().__init__(name, mode, max_concurrent)
        self.api_key = api_key
        self.model = model
        self.fallback_to_local = fallback_to_local
        self._client: Optional[httpx.AsyncClient] = None
        self._local_healer = LocalRemediationEngine(mode=mode, max_concurrent=max_concurrent)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=GROQ_API_BASE,
                timeout=30,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def _call_groq(self, system_prompt: str, user_prompt: str) -> Optional[Dict[str, Any]]:
        try:
            client = await self._get_client()
            resp = await client.post(
                "/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 256,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"].strip()
            content = content.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            return json.loads(content)
        except Exception as e:
            logging.warning("Groq API call failed: %s", e)
            return None

    async def analyze_anomaly(self, anomaly: AnomalyEvent) -> Optional[Dict[str, Any]]:
        user_prompt = (
            f"Service: {anomaly.labels.get('service', 'unknown')}\n"
            f"Metric: {anomaly.metric_name} = {anomaly.metric_value:.2f}\n"
            f"Anomaly Type: {anomaly.anomaly_type.value}\n"
            f"Severity: {anomaly.severity.value}\n"
            f"Score: {anomaly.score:.2f}\n"
            f"Description: {anomaly.description}\n"
            f"Labels: {json.dumps(anomaly.labels)}"
        )
        return await self._call_groq(ANOMALY_SYSTEM_PROMPT, user_prompt)

    async def analyze_prediction(self, prediction: PredictionResult) -> Optional[Dict[str, Any]]:
        user_prompt = (
            f"Metric: {prediction.metric_name}\n"
            f"Current Value: {prediction.current_value:.2f}\n"
            f"Predicted Value: {prediction.predicted_value:.2f}\n"
            f"Upper Bound: {prediction.upper_bound:.2f}\n"
            f"Lower Bound: {prediction.lower_bound:.2f}\n"
            f"Failure Probability: {prediction.failure_probability:.2f}\n"
            f"Time to Failure (min): {prediction.time_to_failure_minutes or 'unknown'}\n"
            f"Confidence: {prediction.confidence:.2f}"
        )
        return await self._call_groq(PREDICTION_SYSTEM_PROMPT, user_prompt)

    async def handle_anomaly(self, anomaly: AnomalyEvent) -> Optional[RemediationAction]:
        if not self.api_key:
            if self.fallback_to_local:
                return await self._local_healer.handle_anomaly(anomaly)
            return None

        decision = await self.analyze_anomaly(anomaly)
        if decision is None:
            if self.fallback_to_local:
                return await self._local_healer.handle_anomaly(anomaly)
            return None

        try:
            action_type = ActionType(decision.get("action_type", "custom"))
            risk = ActionRisk(decision.get("risk", "medium"))
        except ValueError:
            action_type = ActionType.CUSTOM
            risk = ActionRisk.MEDIUM

        target = decision.get("target_service") or anomaly.labels.get("service", anomaly.metric_name)
        playbook = decision.get("playbook_name", "groq_ai_recommended")

        action = self.create_action(
            action_type=action_type,
            risk=risk,
            target=target,
            playbook=playbook,
            triggered_by=f"anomaly:{anomaly.id}",
            parameters={
                "groq_reasoning": decision.get("reasoning", ""),
                "metric_name": anomaly.metric_name,
                "severity": anomaly.severity.value,
                "score": anomaly.score,
            },
        )
        return action

    async def handle_prediction(self, prediction: PredictionResult) -> Optional[RemediationAction]:
        if not self.api_key:
            if self.fallback_to_local:
                return await self._local_healer.handle_prediction(prediction)
            return None

        decision = await self.analyze_prediction(prediction)
        if decision is None:
            if self.fallback_to_local:
                return await self._local_healer.handle_prediction(prediction)
            return None

        try:
            action_type = ActionType(decision.get("action_type", "scale_up"))
            risk = ActionRisk(decision.get("risk", "medium"))
        except ValueError:
            action_type = ActionType.SCALE_UP
            risk = ActionRisk.MEDIUM

        target = decision.get("target_service") or prediction.metric_name.split("_")[0]
        playbook = decision.get("playbook_name", "groq_ai_predictive")

        action = self.create_action(
            action_type=action_type,
            risk=risk,
            target=target,
            playbook=playbook,
            triggered_by=f"prediction:{prediction.metric_name}",
            parameters={
                "groq_reasoning": decision.get("reasoning", ""),
                "failure_probability": prediction.failure_probability,
                "predicted_value": prediction.predicted_value,
                "time_to_failure": prediction.time_to_failure_minutes,
            },
        )
        return action

    async def execute(self, action: RemediationAction) -> RemediationAction:
        action.executed_at = datetime.now(timezone.utc)
        action.status = "running"

        await asyncio.sleep(random.uniform(0.3, 1.0))

        success_prob = 0.88
        if random.random() < success_prob:
            action.status = "completed"
            action.result = f"[Groq AI] Successfully executed {action.action_type.value} on {action.target}"
        else:
            action.status = "failed"
            action.error = f"[Groq AI] Failed to execute {action.action_type.value}: simulated execution error"

        action.completed_at = datetime.now(timezone.utc)
        return action

    async def rollback(self, action: RemediationAction) -> bool:
        await asyncio.sleep(random.uniform(0.3, 1.0))
        return random.random() < 0.92

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    def get_stats(self) -> dict:
        stats = super().get_stats()
        local_stats = self._local_healer.get_stats()
        stats["groq_actions"] = stats["total"]
        stats["local_fallback_actions"] = local_stats["total"]
        stats["mode"] = "groq_ai" if self.api_key else "local_fallback"
        return stats
