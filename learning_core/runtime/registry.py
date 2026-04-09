from __future__ import annotations

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

    def list_operations(self) -> list[str]:
        return sorted(self._skills.keys())

