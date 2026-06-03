#!/usr/bin/env python3
"""Run SH-PDOPS in simulation mode for research data generation."""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.engine import ShPdopsEngine
from src.config.settings import settings


async def simulate(steps: int = 50, fault_step: int = 15):
    engine = ShPdopsEngine()
    results = {
        "timestamps": [],
        "metrics_count": [],
        "anomalies": [],
        "predictions": [],
        "actions": [],
        "health_scores": [],
    }

    print(f"SH-PDOPS Simulation ({steps} steps)")
    print("=" * 50)

    for step in range(steps):
        if step == fault_step:
            engine.collector.enable_fault("cpu_spike")
            print(f"\n[Step {step}] INJECTING FAULT: cpu_spike")

        await engine._tick()

        anomalies = engine.detector._anomalies
        preds = engine.predictor._predictions
        actions = engine.healer._actions
        metrics = engine.collector._buffer

        results["timestamps"].append(datetime.now(timezone.utc).isoformat())
        results["metrics_count"].append(len(metrics))
        results["anomalies"].append(len(anomalies))
        results["predictions"].append(len(preds))
        results["actions"].append(len(actions))

        metrics_dict = {}
        for p in metrics[-10:]:
            key = p.name.split("_", 1)[-1] if "_" in p.name else p.name
            metrics_dict[key] = p.value

        from src.common.utils import compute_health_score
        hs = compute_health_score(metrics_dict)
        results["health_scores"].append(hs)

        if step % 10 == 0 or step == fault_step:
            active_anomalies = [a for a in anomalies if not a.resolved]
            high_risk = [p for p in preds if p.failure_probability > 0.5]
            print(
                f"  Step {step:3d} | Metrics: {len(metrics):4d} | "
                f"Anomalies: {len(active_anomalies):2d} | "
                f"HighRisk: {len(high_risk):2d} | "
                f"Actions: {len(actions):2d} | "
                f"Health: {hs:.1f}%"
            )

        await asyncio.sleep(0.1)

    print("\n" + "=" * 50)
    print("Simulation Complete")
    print(f"Total anomalies detected: {len(engine.detector._anomalies)}")
    print(f"Total predictions made: {len(engine.predictor._predictions)}")
    print(f"Total actions taken: {len(engine.healer._actions)}")
    print(f"Final health score: {results['health_scores'][-1]:.1f}%")

    output_path = Path("data/metrics/simulation_results.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"Results saved to {output_path}")

    return results


if __name__ == "__main__":
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    asyncio.run(simulate(steps=steps))
