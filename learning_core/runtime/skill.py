from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar
from typing import TYPE_CHECKING

from pydantic import BaseModel

from learning_core.observability.traces import ExecutionLineage, ExecutionTrace, PromptPreview
from learning_core.runtime.context import RuntimeContext
from learning_core.runtime.policy import ExecutionPolicy

InputModelT = TypeVar("InputModelT", bound=BaseModel)
OutputModelT = TypeVar("OutputModelT", bound=BaseModel)


@dataclass(frozen=True)
class SkillExecutionResult(Generic[OutputModelT]):
    artifact: OutputModelT
    lineage: ExecutionLineage
    trace: ExecutionTrace


class SkillDefinition(ABC, Generic[InputModelT, OutputModelT]):
    name: str
    input_model: type[InputModelT]
    output_model: type[OutputModelT]
    policy: ExecutionPolicy

    @abstractmethod
    def build_prompt_preview(self, payload: InputModelT, context: RuntimeContext) -> PromptPreview:
        raise NotImplementedError

    @abstractmethod
    def execute(self, engine: "AgentEngine", payload: InputModelT, context: RuntimeContext) -> SkillExecutionResult[OutputModelT]:
        raise NotImplementedError


if TYPE_CHECKING:
    from learning_core.runtime.engine import AgentEngine
