from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay_seconds: int = 5
    max_delay_seconds: int = 60

    def delay_for_attempt(self, attempt: int) -> int:
        if attempt < 1:
            raise ValueError("attempt must be >= 1")
        return min(self.max_delay_seconds, self.base_delay_seconds * (2 ** (attempt - 1)))

    def may_retry(self, *, attempt: int, retryable: bool) -> bool:
        return retryable and attempt < self.max_attempts
