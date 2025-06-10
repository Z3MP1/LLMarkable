"""Utility functions for synthesis."""

import asyncio
import secrets
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, TypeVar

from src.config import Config
from src.exceptions import ProviderAuthenticationError, ProviderError, RateLimitError, SynthesisError
from src.synthesis.circuit_breaker import CircuitBreaker

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable  # noqa: TC004

T = TypeVar("T")


def compute_exponential_backoff(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: float = 0.2,
) -> float:
    """
    Compute exponential backoff delay with jitter.

    Args:
        attempt: Current retry attempt (starting from 1)
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        jitter: Jitter factor (0.0 to 1.0, as a fraction of delay)

    Returns:
        Delay in seconds (float)

    """
    delay: float = min(base_delay * (2 ** (attempt - 1)), max_delay)
    jitter_amount: float = delay * jitter * secrets.SystemRandom().uniform(-1, 1)
    return max(0.0, delay + jitter_amount)


async def async_backoff_sleep(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: float = 0.2,
) -> None:
    """
    Async sleep for exponential backoff with jitter.

    Args:
        attempt: Current retry attempt (starting from 1)
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        jitter: Jitter factor (0.0 to 1.0, as a fraction of delay)

    """
    delay = compute_exponential_backoff(attempt, base_delay, max_delay, jitter)
    await asyncio.sleep(delay)


def resilient_llm_call(
    func: Callable[..., Awaitable[T]],
    config: Config,
    circuit_breaker: CircuitBreaker,
) -> Callable[..., Awaitable[T]]:
    """
    Apply circuit breaker and retry/backoff logic to async LLM provider calls.

    Args:
        func: The async function to wrap (e.g., provider.generate)
        config: Config object with retry/backoff/circuit breaker settings
        circuit_breaker: CircuitBreaker instance to use

    Returns:
        Wrapped async function with resilience logic

    """

    async def wrapper(*args: object, **kwargs: object) -> T:
        last_exc: Exception | None = None
        for attempt in range(1, config.max_retries + 2):  # +1 for initial try
            try:
                return await circuit_breaker.call(func, *args, **kwargs)
            except (RateLimitError, ProviderAuthenticationError, ProviderError, SynthesisError) as err:
                last_exc = err
                if attempt > config.max_retries:
                    raise
                await async_backoff_sleep(
                    attempt,
                    base_delay=config.base_delay,
                    max_delay=float(config.circuit_breaker_timeout),
                    jitter=0.2,
                )
            except Exception:
                # For unexpected errors, do not retry
                raise
        if last_exc is not None:
            raise last_exc
        msg = "Resilience logic failed unexpectedly."
        raise RuntimeError(msg)

    return wrapper
