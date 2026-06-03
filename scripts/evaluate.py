#!/usr/bin/env python3
"""Evaluate SH-PDOPS performance metrics for research."""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.engine import ShPdopsEngine


async def evaluate(runs: int = 3, steps_per_run: int = 100):
    print(f"SH-PDOPS Evaluation ({runs} runs, {steps_per_run} steps each)")
    print("=" * 60)

    all_results = []

    for run in range(runs):
        print(f"\nRun {run + 1}/{runs}")
        engine = ShPdopsEngine()

        fault_injected = False
        for step in range(steps_per_run):
            # Inject fault midway
            if step == steps_per_run // 2 and not fault_injected:
                engine.collector.enable_fault("error_burst")
                fault_injected = True
                print(f"  [Step {step}] Fault injected")

            await engine._tick()

            if step == steps_per_run // 2 + 10:
                engine.collector.disable_fault()

        # Collect run metrics
        anomalies = engine.detector._anomalies
        predictions = engine.predictor._predictions
        actions = engine.healer._actions

        resolved = sum(1 for a in anomalies if a.resolved)
        active = len(anomalies) - resolved
        successful_actions = sum(1 for a in actions if a.status == "completed" and a.error is None)
        failed_actions = sum(1 for a in actions if a.status == "failed")

        run_result = {
            "run": run + 1,
            "total_anomalies": len(anomalies),
            "resolved_anomalies": resolved,
            "active_anomalies": active,
            "total_predictions": len(predictions),
            "total_actions": len(actions),
            "successful_actions": successful_actions,
            "failed_actions": failed_actions,
            "action_success_rate": (successful_actions / max(len(actions), 1)) * 100,
            "resolution_rate": (resolved / max(len(anomalies), 1)) * 100,
        }

        avg_failure_prob = 0.0
        if predictions:
            avg_failure_prob = (
                sum(p.failure_probability for p in predictions) / len(predictions)
            )
        run_result["avg_failure_probability"] = round(avg_failure_prob * 100, 2)

        high_risk = [p for p in predictions if p.failure_probability > 0.5]
        run_result["high_risk_predictions"] = len(high_risk)

        all_results.append(run_result)
        print(f"  Anomalies: {len(anomalies)} | Resolved: {resolved} | "
              f"Actions: {len(actions)} ({successful_actions} ok, "
              f"{failed_actions} failed)")
        print(f"  Predictions: {len(predictions)} | "
              f"High-risk: {len(high_risk)} | "
              f"Avg failure prob: {run_result['avg_failure_probability']:.1f}%")

    # Aggregated results
    print("\n" + "=" * 60)
    print("AGGREGATED RESULTS")
    print("=" * 60)

    avg_anomalies = sum(r["total_anomalies"] for r in all_results) / runs
    avg_resolved = sum(r["resolved_anomalies"] for r in all_results) / runs
    avg_actions = sum(r["total_actions"] for r in all_results) / runs
    avg_success_rate = sum(r["action_success_rate"] for r in all_results) / runs
    avg_resolution = sum(r["resolution_rate"] for r in all_results) / runs
    avg_failure_prob = sum(r["avg_failure_probability"] for r in all_results) / runs

    summary = {
        "runs": runs,
        "steps_per_run": steps_per_run,
        "avg_anomalies_per_run": round(avg_anomalies, 1),
        "avg_resolved_per_run": round(avg_resolved, 1),
        "avg_actions_per_run": round(avg_actions, 1),
        "avg_action_success_rate": round(avg_success_rate, 1),
        "avg_anomaly_resolution_rate": round(avg_resolution, 1),
        "avg_failure_probability": round(avg_failure_prob, 1),
        "runs_data": all_results,
    }

    print(f"Avg anomalies/run: {avg_anomalies:.1f}")
    print(f"Avg resolved/run:  {avg_resolved:.1f}")
    print(f"Avg actions/run:   {avg_actions:.1f}")
    print(f"Action success:     {avg_success_rate:.1f}%")
    print(f"Resolution rate:    {avg_resolution:.1f}%")
    print(f"Avg failure prob:   {avg_failure_prob:.1f}%")

    output_path = Path("data/metrics/evaluation_results.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"\nResults saved to {output_path}")

    return summary


if __name__ == "__main__":
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    steps = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    asyncio.run(evaluate(runs=runs, steps_per_run=steps))
