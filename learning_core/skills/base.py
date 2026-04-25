from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any

from learning_core.observability.traces import PromptPreview
from learning_core.runtime.skill import SkillDefinition, SkillExecutionResult


class StructuredOutputSkill(SkillDefinition):
    skill_file: str = "SKILL.md"

    def build_user_prompt(self, payload, context) -> str:  # pragma: no cover - implemented by subclasses
        raise NotImplementedError

    def build_user_message_content(
        self,
        payload,
        context,
        *,
        prompt_text: str | None = None,
        provider: str | None = None,
    ) -> str | list[dict[str, Any]]:
        del provider
        return prompt_text if prompt_text is not None else self.build_user_prompt(payload, context)

    def build_prompt_preview(self, payload, context) -> PromptPreview:
        return PromptPreview(
            system_prompt=self.read_skill_markdown(),
            user_prompt=self.build_user_prompt(payload, context),
        )

    def repair_invalid_artifact(self, *, raw_artifact, payload, context, error):
        return None

    def validate_artifact_semantics(self, *, artifact, payload, context) -> list[str]:
        return []

    def build_validation_retry_preview(
        self,
        *,
        payload,
        context,
        raw_artifact,
        error,
    ) -> PromptPreview | None:
        return None

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
