"""Circuit breaker for LLM/HTTP provider calls."""

from __future__ import annotations

import asyncio
import time
from enum import Enum, auto
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

T = TypeVar("T")


class CircuitBreakerState(Enum):
    """Circuit breaker states."""

    CLOSED = auto()
    OPEN = auto()
    HALF_OPEN = auto()


class CircuitBreaker:
    """
    Async-compatible Circuit Breaker for LLM/HTTP provider calls.

    Usage:
        cb = CircuitBreaker(failure_threshold=5, reset_timeout=30, exceptions=(TimeoutError,))
        result = await cb.call(some_async_func, *args, **kwargs)

        # Or as a decorator:
        @cb
        async def provider_call(...):
            ...
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        reset_timeout: float = 30.0,
        exceptions: tuple[type[BaseException], ...] = (Exception,),
        name: str | None = None,
    ) -> None:
        """
        Initialize the circuit breaker.

        Args:
            failure_threshold: Number of consecutive failures to open the circuit
            reset_timeout: Time (seconds) to stay open before trying half-open
            exceptions: Exception types to treat as failures
            name: Optional name for monitoring/debugging

        """
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.exceptions = exceptions
        self.name = name or "CircuitBreaker"

        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._opened_since = 0.0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitBreakerState:
        """Get the current state of the circuit breaker."""
        return self._state

    @property
    def failure_count(self) -> int:
        """Get the number of consecutive failures."""
        return self._failure_count

    def _current_time(self) -> float:
        return time.monotonic()

    async def _trip(self) -> None:
        self._state = CircuitBreakerState.OPEN
        self._opened_since = self._current_time()

    async def _reset(self) -> None:
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._opened_since = 0.0

    async def _half_open(self) -> None:
        self._state = CircuitBreakerState.HALF_OPEN

    async def _maybe_reset(self) -> None:
        if self._state == CircuitBreakerState.OPEN and self._current_time() - self._opened_since >= self.reset_timeout:
            await self._half_open()

    async def call(self, func: Callable[..., Awaitable[T]], *args: object, **kwargs: object) -> T:
        """
        Call an async function with circuit breaker protection.

        Args:
            func: Async function to call
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function

        Returns:
            Result of the function call

        Raises:
            Exception: If the circuit is open or the function fails

        """
        async with self._lock:
            await self._maybe_reset()
            state = self._state

        if state == CircuitBreakerState.OPEN:
            msg = f"Circuit '{self.name}' is OPEN (failures: {self._failure_count})"
            raise RuntimeError(msg)

        if state == CircuitBreakerState.HALF_OPEN:
            # Allow a single trial call
            try:
                result = await func(*args, **kwargs)
            except self.exceptions:
                async with self._lock:
                    await self._trip()
                raise
            else:
                async with self._lock:
                    await self._reset()
                return result

        # CLOSED state
        try:
            result = await func(*args, **kwargs)
        except self.exceptions:
            async with self._lock:
                self._failure_count += 1
                if self._failure_count >= self.failure_threshold:
                    await self._trip()
            raise
        else:
            async with self._lock:
                self._failure_count = 0
            return result

    def __call__(self, func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        """Decorate an async function with circuit breaker protection."""

        async def wrapper(*args: object, **kwargs: object) -> T:
            return await self.call(func, *args, **kwargs)

        return wrapper
