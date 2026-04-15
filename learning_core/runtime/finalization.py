from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel

from learning_core.observability.traces import ExecutionLineage, ExecutionTrace


@dataclass(frozen=True)
class KernelExecutionResult:
    artifact: BaseModel
    lineage: ExecutionLineage
    trace: ExecutionTrace
