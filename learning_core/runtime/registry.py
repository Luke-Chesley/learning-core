from __future__ import annotations

from learning_core.contracts.responses import OperationDescriptor
from learning_core.runtime.errors import SkillNotFoundError
from learning_core.runtime.skill import SkillDefinition


class SkillRegistry:
    def __init__(self) -> None:
        self._skills: dict[str, SkillDefinition] = {}

    def register(self, operation_name: str, skill: SkillDefinition) -> None:
        self._skills[operation_name] = skill

    def get(self, operation_name: str) -> SkillDefinition:
        skill = self._skills.get(operation_name)
        if skill is None:
            raise SkillNotFoundError(f"Unknown operation '{operation_name}'.")
        return skill

    def list_operations(self) -> list[OperationDescriptor]:
        return sorted(
            [
                OperationDescriptor(
                    operation_name=operation_name,
                    skill_name=skill.name,
                    skill_version=skill.policy.skill_version,
                    task_kind=skill.policy.task_kind,
                    allowed_tools=list(skill.policy.allowed_tools),
                )
                for operation_name, skill in self._skills.items()
            ],
            key=lambda descriptor: descriptor.operation_name,
        )
