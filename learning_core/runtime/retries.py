from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 1
    repair_attempts: int = 0
    max_loop_steps: int = 0
