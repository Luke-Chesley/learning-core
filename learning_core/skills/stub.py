from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel

from learning_core.observability.traces import PromptPreview
from learning_core.runtime.context import RuntimeContext
from learning_core.runtime.errors import SkillNotImplementedError
from learning_core.runtime.policy import ExecutionPolicy
from learning_core.runtime.skill import SkillDefinition


@dataclass(frozen=True)
class StubSkillConfig:
    name: str
    operation_name: str
    skill_version: str
    input_model: type[BaseModel]
    output_model: type[BaseModel]


class UnimplementedSkill(SkillDefinition):
    def __init__(self, config: StubSkillConfig) -> None:
        self.name = config.name
        self.input_model = config.input_model
        self.output_model = config.output_model
        self.policy = ExecutionPolicy(
            skill_name=config.name,
            skill_version=config.skill_version,
            allowed_tools=(),
        )

    def build_prompt_preview(self, payload: BaseModel) -> PromptPreview:
        return PromptPreview(
            system_prompt="Unimplemented skill scaffold.",
            user_prompt=payload.model_dump_json(indent=2),
        )

    def execute(self, engine, payload: BaseModel, context: RuntimeContext):
        raise SkillNotImplementedError(
            f"Skill '{self.name}' is scaffolded but not implemented yet."
        )

