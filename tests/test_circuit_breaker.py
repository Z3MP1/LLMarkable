"""Test the circuit breaker."""

import asyncio

import pytest

from src.synthesis.circuit_breaker import CircuitBreaker, CircuitBreakerState


@pytest.mark.asyncio
async def test_circuit_success_path() -> None:
    """Test that the circuit breaker opens on failures."""
    cb = CircuitBreaker(failure_threshold=3, reset_timeout=1.0, exceptions=(RuntimeError,))

    async def ok() -> int:
        return 42

    for _ in range(5):
        assert await cb.call(ok) == 42
        assert cb.state == CircuitBreakerState.CLOSED


@pytest.mark.asyncio
async def test_circuit_opens_on_failures() -> None:
    """Test that the circuit breaker opens on failures."""
    cb = CircuitBreaker(failure_threshold=2, reset_timeout=1.0, exceptions=(ValueError,))

    async def fail() -> None:
        raise ValueError("fail")

    with pytest.raises(ValueError):
        await cb.call(fail)
    assert cb.state == CircuitBreakerState.CLOSED
    with pytest.raises(ValueError):
        await cb.call(fail)
    assert cb.state == CircuitBreakerState.OPEN
    with pytest.raises(RuntimeError):
        await cb.call(fail)


@pytest.mark.asyncio
async def test_circuit_half_open_and_recovery() -> None:
    """Test that the circuit breaker opens on failures."""
    cb = CircuitBreaker(failure_threshold=1, reset_timeout=0.5, exceptions=(ValueError,))

    async def fail() -> None:
        raise ValueError("fail")

    async def ok() -> str:
        return "ok"

    with pytest.raises(ValueError):
        await cb.call(fail)
    assert cb.state == CircuitBreakerState.OPEN
    with pytest.raises(RuntimeError):
        await cb.call(ok)
    await asyncio.sleep(0.6)
    # Now should be HALF_OPEN, allow one call
    assert await cb.call(ok) == "ok"
    assert cb.state == CircuitBreakerState.CLOSED


@pytest.mark.asyncio
async def test_exception_propagation() -> None:
    """Test that the circuit breaker propagates exceptions."""
    cb = CircuitBreaker(failure_threshold=2, reset_timeout=1.0, exceptions=(ValueError,))

    async def fail() -> None:
        raise ValueError("fail")

    with pytest.raises(ValueError):
        await cb.call(fail)


@pytest.mark.asyncio
async def test_threshold_one() -> None:
    """Test that the circuit breaker opens on failures."""
    cb = CircuitBreaker(failure_threshold=1, reset_timeout=0.1, exceptions=(ValueError,))

    async def fail() -> None:
        raise ValueError("fail")

    with pytest.raises(ValueError):
        await cb.call(fail)
    assert cb.state == CircuitBreakerState.OPEN


@pytest.mark.asyncio
async def test_async_safety() -> None:
    """Test that the circuit breaker is async safe."""
    cb = CircuitBreaker(failure_threshold=3, reset_timeout=1.0, exceptions=(ValueError,))

    async def ok() -> int:
        await asyncio.sleep(0.01)
        return 1

    results = await asyncio.gather(*(cb.call(ok) for _ in range(10)))
    assert all(r == 1 for r in results)
    assert cb.state == CircuitBreakerState.CLOSED
