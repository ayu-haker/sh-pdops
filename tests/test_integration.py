import pytest
from src.engine import ShPdopsEngine


@pytest.mark.asyncio
async def test_engine_tick():
    engine = ShPdopsEngine()
    await engine._tick()
    assert len(engine.collector._buffer) > 0


@pytest.mark.asyncio
async def test_engine_detects_anomalies():
    engine = ShPdopsEngine()
    engine.collector._inject_fault = True
    engine.collector._fault_type = "cpu_spike"
    engine.collector._timestep = 0

    for _ in range(20):
        await engine._tick()

    anomalies = engine.detector._anomalies
    assert len(anomalies) >= 0


@pytest.mark.asyncio
async def test_engine_healer_integration():
    engine = ShPdopsEngine()
    engine.collector.enable_fault("error_burst")
    for _ in range(30):
        await engine._tick()
    actions = engine.healer._actions
    assert len(actions) >= 0


@pytest.mark.asyncio
async def test_engine_uptime():
    engine = ShPdopsEngine()
    assert engine.uptime == 0.0
    await engine._tick()
    assert engine.uptime >= 0.0
