from __future__ import annotations
import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Callable, TypeVar

T=TypeVar('T')


class FaultMode(StrEnum):
    TIMEOUT = 'timeout'
    ERROR = 'error'
    LATENCY = 'latency'


@dataclass(frozen=True)
class FaultProfile:
    dependency: str
    mode: FaultMode
    latency_ms: int = 0
    error_message: str = 'synthetic dependency failure'


class ControlledFaultInjector:
    """Test/staging-only deterministic fault injector.

    It intentionally refuses production so application code cannot turn a test
    helper into an unreviewed production failure mechanism.
    """
    def __init__(self, *, environment: str, explicitly_authorized: bool = False):
        env=environment.strip().lower()
        if env in {'prod','production'}:
            raise RuntimeError('application-level fault injection is forbidden in production')
        if not explicitly_authorized:
            raise RuntimeError('fault injection requires explicit authorization')
        self.environment=env

    def call(self, profile: FaultProfile, fn: Callable[[], T]) -> T:
        if profile.mode is FaultMode.LATENCY:
            time.sleep(max(0, profile.latency_ms)/1000.0)
            return fn()
        if profile.mode is FaultMode.TIMEOUT:
            raise TimeoutError(profile.error_message)
        if profile.mode is FaultMode.ERROR:
            raise RuntimeError(profile.error_message)
        return fn()
