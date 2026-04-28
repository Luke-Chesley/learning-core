from __future__ import annotations

import json

from learning_core.contracts.source_interpret import (
    SourceInterpretationArtifact,
    SourceInterpretationRequest,
)
from learning_core.observability.traces import PromptPreview
from learning_core.runtime.policy import ExecutionPolicy
from learning_core.skills.base import StructuredOutputSkill
from learning_core.skills.prompt_utils import (
    append_user_authored_context,
    build_openai_file_blocks,
    format_source_files,
)


def _collect_grounded_chunks(values: list[str], chunk: str | None) -> None:
    normalized = (chunk or "").strip()
    if not normalized or normalized in values:
        return
    values.append(normalized)


def _extend_grounded_chunks(values: list[str], chunks) -> None:
    if not isinstance(chunks, list):
        return

    for chunk in chunks:
        if isinstance(chunk, str):
            _collect_grounded_chunks(values, chunk)
            continue
        if isinstance(chunk, dict):
            for key in ("title", "label", "name", "text"):
                maybe_value = chunk.get(key)
                if isinstance(maybe_value, str):
                    _collect_grounded_chunks(values, maybe_value)
                    break


def _derive_detected_chunks(payload: SourceInterpretationRequest) -> list[str]:
    derived: list[str] = []

    for source_package in payload.sourcePackages:
        _extend_grounded_chunks(derived, source_package.detectedChunks)

    structure = payload.extractedStructure or {}
    if isinstance(structure, dict):
        for key in ("detectedChunks", "headings", "sections", "chapters", "units", "topics"):
            _extend_grounded_chunks(derived, structure.get(key))

    for text in (payload.extractedText, payload.rawText):
        if not text:
            continue
        for line in text.splitlines():
            _collect_grounded_chunks(derived, line)

    return derived[:6]


class SourceInterpretSkill(StructuredOutputSkill):
    name = "source_interpret"
    input_model = SourceInterpretationRequest
    output_model = SourceInterpretationArtifact
    policy = ExecutionPolicy(
        skill_name="source_interpret",
        skill_version="2026-04-17",
        max_tokens=2500,
    )

    def build_user_prompt(self, payload: SourceInterpretationRequest, context) -> str:
        lines = [
            f"Requested route: {payload.requestedRoute}",
            f"Input modalities: {', '.join(payload.inputModalities) if payload.inputModalities else 'none'}",
            f"Asset refs: {len(payload.assetRefs)}",
            f"Title candidate: {payload.titleCandidate or 'None provided'}",
            f"Learner: {payload.learnerName or 'Unknown learner'}",
            "",
            "Source packages:",
            json.dumps([source.model_dump(mode="json") for source in payload.sourcePackages], indent=2),
            "",
            "Attached source files:",
            format_source_files(payload.sourceFiles),
            "",
            "Extracted structure:",
            json.dumps(payload.extractedStructure or {}, indent=2),
            "",
            "Raw text:",
            payload.rawText or "None provided.",
            "",
            "Extracted text:",
            payload.extractedText,
        ]
        append_user_authored_context(lines, context)
        lines.extend(
            [
                "",
                "Interpret the source only.",
                "When attached source files are present, treat them as the authoritative source and use the raw or extracted text as supporting note context.",
                "This is not a planning step. Do not generate curriculum, lesson steps, activities, pacing, or delivery plans.",
                "Return only valid JSON.",
            ]
        )
        return "\n".join(lines)

    def build_user_message_content(
        self,
        payload: SourceInterpretationRequest,
        context,
        *,
        prompt_text: str | None = None,
        provider: str | None = None,
    ) -> str | list[dict]:
        prompt = prompt_text if prompt_text is not None else self.build_user_prompt(payload, context)
        if provider != "openai" or not payload.sourceFiles:
            return prompt
        return [{"type": "text", "text": prompt}, *build_openai_file_blocks(payload.sourceFiles)]

    def repair_invalid_artifact(self, *, raw_artifact, payload, context, error):
        if not isinstance(raw_artifact, dict):
            return None

        repaired = dict(raw_artifact)
        source_kind = repaired.get("sourceKind")
        confidence = repaired.get("confidence")
        if not isinstance(source_kind, str):
            return None

        if repaired.get("entryLabel") is None:
            repaired["entryLabel"] = None

        if repaired.get("planningConstraints") is None:
            repaired["planningConstraints"] = {}

        if repaired.get("followUpQuestion") is None:
            repaired["followUpQuestion"] = None

        if repaired.get("needsConfirmation") is None:
            repaired["needsConfirmation"] = bool(confidence == "low" or source_kind == "ambiguous")

        if repaired.get("assumptions") is None:
            repaired["assumptions"] = []
        if not repaired.get("detectedChunks"):
            repaired["detectedChunks"] = _derive_detected_chunks(payload)

        return repaired if repaired != raw_artifact else None

    def build_validation_retry_preview(
        self,
        *,
        payload,
        context,
        raw_artifact,
        error,
    ) -> PromptPreview | None:
        system_prompt = "\n\n".join(
            [
                self.read_skill_markdown(),
                "Repair instructions:",
                "- The previous response was invalid.",
                "- Return only one corrected JSON object.",
                "- Every response must include all required keys.",
                "- `recommendedHorizon`, `entryStrategy`, `continuationMode`, and `deliveryPattern` are required and may never be omitted.",
                "- `planningConstraints` is required; use an empty object when no constraints were stated.",
                "- Do not infer missing enum fields from sourceKind using fallback defaults. Repair only nullables, assumptions, detectedChunks, and needsConfirmation when allowed.",
                "- If the source is weak or ambiguous, choose conservative grounded values instead of omitting required fields.",
                "- This skill is interpretation-only, not planning.",
                "- Include all required contract fields explicitly in the corrected JSON.",
            ]
        )
        user_prompt = "\n".join(
            [
                self.build_user_prompt(payload, context),
                "",
                "Previous invalid JSON:",
                json.dumps(raw_artifact, indent=2, ensure_ascii=True),
                "",
                f"Validation error: {error}",
                "",
                "Repair the JSON so it matches the exact schema. Return only the corrected JSON object.",
            ]
        )
        return PromptPreview(system_prompt=system_prompt, user_prompt=user_prompt)
