from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.domain.mcp import MCPCircuitState, MCPPolicyError


@dataclass
class _Circuit:
    failures: int = 0
    opened_at: datetime | None = None
    state: MCPCircuitState = MCPCircuitState.CLOSED


class CircuitBreakerRegistry:
    def __init__(self, *, failure_threshold: int = 3, recovery_seconds: int = 30) -> None:
        self.failure_threshold = max(1, failure_threshold)
        self.recovery_seconds = max(1, recovery_seconds)
        self._states: dict[str, _Circuit] = {}

    def before_call(self, tool_name: str) -> None:
        circuit = self._states.setdefault(tool_name, _Circuit())
        if circuit.state is not MCPCircuitState.OPEN:
            return
        now = datetime.now(timezone.utc)
        if circuit.opened_at and now - circuit.opened_at >= timedelta(seconds=self.recovery_seconds):
            circuit.state = MCPCircuitState.HALF_OPEN
            return
        raise MCPPolicyError(f"tool circuit is open: {tool_name}")

    def success(self, tool_name: str) -> None:
        self._states[tool_name] = _Circuit()

    def failure(self, tool_name: str) -> None:
        circuit = self._states.setdefault(tool_name, _Circuit())
        circuit.failures += 1
        if circuit.failures >= self.failure_threshold:
            circuit.state = MCPCircuitState.OPEN
            circuit.opened_at = datetime.now(timezone.utc)

    def state(self, tool_name: str) -> MCPCircuitState:
        return self._states.get(tool_name, _Circuit()).state
