import pytest
from src.collector.simulator import SimulatedCollector
from src.common.types import MetricPoint


@pytest.mark.asyncio
async def test_simulator_collects_points():
    collector = SimulatedCollector()
    points = await collector.collect()

    assert len(points) > 0
    assert all(isinstance(p, MetricPoint) for p in points)


@pytest.mark.asyncio
async def test_simulator_service_names():
    collector = SimulatedCollector()
    assert len(collector.get_service_names()) == 6
    assert "api-gateway" in collector.get_service_names()


@pytest.mark.asyncio
async def test_simulator_fault_injection():
    collector = SimulatedCollector()
    before = await collector.collect()
    cpu_before = [p.value for p in before if "cpu" in p.name and "api-gateway" in p.name]
    avg_before = sum(cpu_before) / len(cpu_before) if cpu_before else 0

    collector.enable_fault("cpu_spike")

    during = await collector.collect()
    cpu_during = [p.value for p in during if "cpu" in p.name and "api-gateway" in p.name]
    avg_during = sum(cpu_during) / len(cpu_during) if cpu_during else 0

    assert avg_during > avg_before


@pytest.mark.asyncio
async def test_simulator_buffer():
    collector = SimulatedCollector()
    await collector.collect()
    await collector.collect()
    assert len(collector._buffer) > 0
    buffered = collector.get_buffered(minutes=60)
    assert len(buffered) > 0


@pytest.mark.asyncio
async def test_simulator_all_metric_types():
    collector = SimulatedCollector()
    points = await collector.collect()
    types_found = set(p.type for p in points)
    assert len(types_found) >= 5
