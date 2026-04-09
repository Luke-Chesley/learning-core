from __future__ import annotations

import inspect
from pathlib import Path

from learning_core.observability.traces import PromptPreview
from learning_core.runtime.skill import SkillDefinition, SkillExecutionResult


class StructuredOutputSkill(SkillDefinition):
    skill_file: str = "SKILL.md"

    def build_user_prompt(self, payload, context) -> str:  # pragma: no cover - implemented by subclasses
        raise NotImplementedError

    def build_prompt_preview(self, payload, context) -> PromptPreview:
        return PromptPreview(
            system_prompt=self.read_skill_markdown(),
            user_prompt=self.build_user_prompt(payload, context),
        )

    def read_skill_markdown(self) -> str:
        skill_module_path = Path(inspect.getfile(type(self))).resolve()
        for candidate_dir in skill_module_path.parents:
            skill_markdown_path = candidate_dir / self.skill_file
            if skill_markdown_path.exists():
                return skill_markdown_path.read_text(encoding="utf-8").strip()
        raise FileNotFoundError(
            f"Could not find {self.skill_file} for {type(self).__name__} starting at {skill_module_path}"
        )

    def execute(self, engine, payload, context) -> SkillExecutionResult:
        artifact, lineage, trace = engine.run_structured_output(
            skill=self,
            payload=payload,
            context=context,
        )
        return SkillExecutionResult(
            artifact=artifact,
            lineage=lineage,
            trace=trace,
        )
