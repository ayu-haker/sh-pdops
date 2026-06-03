import math
import random
from datetime import datetime, timezone
from typing import List

import numpy as np

from src.collector.base import MetricCollector
from src.common.types import MetricPoint, MetricType


class SimulatedCollector(MetricCollector):
    def __init__(self, name: str = "simulator"):
        super().__init__(name)
        self.service_names = [
            "api-gateway", "user-service", "order-service",
            "payment-service", "notification-service", "db-primary",
        ]
        self._timestep = 0
        self._base_values: dict = {}
        self._drift: dict = {}
        self._inject_fault = False
        self._fault_type: str | None = None
        self._fault_start: int = 0
        self._fault_duration = 20

        for svc in self.service_names:
            self._base_values[svc] = {
                "cpu": random.uniform(20, 40),
                "memory": random.uniform(40, 60),
                "disk": random.uniform(30, 50),
                "latency": random.uniform(50, 100),
                "error_rate": random.uniform(0.1, 1.0),
                "request_rate": random.uniform(100, 500),
            }
            self._drift[svc] = {
                k: random.uniform(-1, 1) for k in self._base_values[svc]
            }

    def enable_fault(self, fault_type: str = "cpu_spike") -> None:
        self._inject_fault = True
        self._fault_type = fault_type
        self._fault_start = self._timestep

    def disable_fault(self) -> None:
        self._inject_fault = False
        self._fault_type = None

    def _apply_fault(self, svc: str, metric: str, base: float) -> float:
        if not self._inject_fault:
            return base
        elapsed = self._timestep - self._fault_start
        if elapsed > self._fault_duration:
            self.disable_fault()
            return base

        intensity = max(0, 1.0 - (elapsed / self._fault_duration))
        if self._fault_type == "cpu_spike" and metric == "cpu":
            return base + 60 * intensity + random.uniform(0, 10)
        if self._fault_type == "memory_leak" and metric == "memory":
            return base + 40 * intensity + random.uniform(0, 5)
        if self._fault_type == "latency_burst" and metric == "latency":
            return base + 400 * intensity + random.uniform(0, 50)
        if self._fault_type == "error_burst" and metric == "error_rate":
            return base + 20 * intensity + random.uniform(0, 5)
        if self._fault_type == "traffic_surge" and metric == "request_rate":
            return base + 2000 * intensity + random.uniform(0, 200)
        return base

    async def collect(self) -> List[MetricPoint]:
        self._timestep += 1
        points: List[MetricPoint] = []

        t = self._timestep * 0.1
        for svc in self.service_names:
            for metric, base in self._base_values[svc].items():
                drift = self._drift[svc][metric]
                time_signal = 10 * math.sin(t + hash(svc) % 10)
                noise = random.gauss(0, base * 0.05)
                diurnal = 15 * math.sin(t * 0.1 + hash(svc + metric) % 24)

                raw = base + drift * 5 + time_signal * 0.5 + diurnal + noise

                raw = self._apply_fault(svc, metric, raw)

                value = max(0.0, raw)

                mtype = MetricType(metric) if metric in [e.value for e in MetricType] else MetricType.CUSTOM
                point = self.make_point(
                    name=f"{svc}_{metric}",
                    value=round(value, 2),
                    type=mtype,
                    labels={"service": svc, "metric": metric},
                )
                points.append(point)

        self.add_to_buffer(points)
        return points

    def get_service_names(self) -> List[str]:
        return self.service_names
