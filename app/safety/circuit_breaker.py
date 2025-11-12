# app/safety/circuit_breaker.py
'''Patient safety circuit breaker'''

import asyncio
import time
from enum import Enum
from functools import wraps
from typing import Callable


class CircuitState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class AsyncCircuitBreaker:
    def __init__(
            self,
            failure_threshold: int = 5,
            timeout: float = 2.0,
            recovery_timeout: float = 30.0
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.recovery_timeout = recovery_timeout

        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        self._lock = asyncio.Lock()

    @staticmethod
    def protected(func: Callable):
        """Decorator for async functions"""

        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            breaker = getattr(self, 'circuit_breaker', None)
            if not breaker:
                return await func(self, *args, **kwargs)

            return await breaker.call(func, self, *args, **kwargs)

        return wrapper

    async def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        async with self._lock:
            # Check if circuit is open
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                else:
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker is OPEN. Retry after {self.recovery_timeout}s"
                    )

        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.timeout
            )

            # Success - reset failure count
            async with self._lock:
                if self.state == CircuitState.HALF_OPEN:
                    self.state = CircuitState.CLOSED
                self.failure_count = 0

            return result

        except (asyncio.TimeoutError, Exception) as e:
            async with self._lock:
                self.failure_count += 1
                self.last_failure_time = time.time()

                if self.failure_count >= self.failure_threshold:
                    self.state = CircuitState.OPEN
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker OPENED after {self.failure_count} failures"
                    ) from e

            raise

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery"""
        if self.last_failure_time is None:
            return True

        return (time.time() - self.last_failure_time) >= self.recovery_timeout


class CircuitBreakerOpenError(Exception):
    pass