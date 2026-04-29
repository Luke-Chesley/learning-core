from __future__ import annotations

import json
import math
import re
from typing import Any

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


NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "twelve": 12,
}


def _number_from_text(value: str) -> int | None:
    if value.isdigit():
        return int(value)
    return NUMBER_WORDS.get(value.lower())


def _source_text_for_pacing(payload: SourceInterpretationRequest, artifact: dict[str, Any]) -> str:
    pieces: list[str] = [
        payload.rawText or "",
        payload.extractedText or "",
        payload.titleCandidate or "",
    ]

    for source_package in payload.sourcePackages:
        pieces.extend(
            [
                source_package.title,
                source_package.summary,
                *source_package.detectedChunks,
            ]
        )

    planning_constraints = artifact.get("planningConstraints")
    if isinstance(planning_constraints, dict):
        pieces.extend(
            str(value)
            for value in [
                planning_constraints.get("practiceCadence"),
                planning_constraints.get("learnerContext"),
                planning_constraints.get("gradeLevel"),
            ]
            if value
        )
        notes = planning_constraints.get("notes")
        if isinstance(notes, list):
            pieces.extend(str(note) for note in notes if note)

    for key in ("assumptions", "detectedChunks"):
        values = artifact.get(key)
        if isinstance(values, list):
            pieces.extend(str(value) for value in values if value)

    return "\n".join(pieces).lower()


def _infer_age_years(text: str) -> int | None:
    match = re.search(r"\b(\d{1,2})\s*[- ]?year[- ]?old\b", text)
    if match:
        return int(match.group(1))
    if re.search(r"\b(preschool|kindergarten|kindergartener)\b", text):
        return 5
    return None


def _infer_total_sessions(text: str) -> int | None:
    match = re.search(
        r"\b(\d{1,3}|one|two|three|four|five|six|seven|eight|nine|ten|twelve)\s+"
        r"(?:total\s+)?(?:sessions?|lessons?|days?)\b(?!\s+per\s+week)",
        text,
        re.IGNORECASE,
    )
    if not match:
        return None
    parsed = _number_from_text(match.group(1))
    return parsed if parsed and parsed > 0 else None


def _infer_total_weeks(text: str) -> tuple[int | None, str | None, bool]:
    explicit_week = re.search(
        r"\b(?:in|over|across|for|within)\s+(\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten|twelve)\s+weeks?\b",
        text,
        re.IGNORECASE,
    )
    if explicit_week:
        parsed = _number_from_text(explicit_week.group(1))
        if parsed:
            return parsed, f"Explicitly stated {parsed} week horizon.", True

    explicit_days = re.search(
        r"\b(?:in|over|across|for|within|next)\s+(\d{1,3})\s+days?\b",
        text,
        re.IGNORECASE,
    )
    if explicit_days:
        parsed_days = int(explicit_days.group(1))
        return max(1, math.ceil(parsed_days / 7)), f"Converted {parsed_days} days into a weekly planning horizon.", True

    if re.search(r"\b(?:this|one)\s+week\b|\bweeklong\b", text):
        return 1, "Interpreted this week as a one-week horizon.", True
    if re.search(r"\b(?:this|one)\s+month\b|\bmonthly\b", text):
        return 4, "Defaulted a month horizon to 4 weeks.", False
    if re.search(r"\b(?:summer|summer break|over summer)\b", text):
        return 8, "Defaulted a summer horizon to 8 weeks.", False
    if re.search(r"\b(?:semester|term)\b", text):
        return 16, "Defaulted a semester horizon to 16 weeks.", False
    if re.search(r"\b(?:quarter|first quarter|second quarter)\b", text):
        return 9, "Defaulted a quarter horizon to 9 weeks.", False
    if re.search(r"\b(?:school year|full year|academic year)\b", text):
        return 36, "Defaulted a school-year horizon to 36 weeks.", False
    if re.search(r"\b(?:long weekend)\b", text):
        return 1, "Interpreted a long weekend as a one-week planning horizon.", False

    return None, None, False


def _infer_sessions_per_week(text: str) -> tuple[int | None, str | None, bool]:
    explicit = re.search(
        r"\b(\d{1,2}|one|two|three|four|five|six|seven)\s+"
        r"(?:short\s+|focused\s+|deep\s+|brief\s+)?(?:sessions?|lessons?|days?)\s+per\s+week\b",
        text,
        re.IGNORECASE,
    )
    if explicit:
        parsed = _number_from_text(explicit.group(1))
        if parsed:
            return parsed, f"Explicitly stated {parsed} sessions per week.", True

    if re.search(r"\b(?:once|one time)\s+a\s+week\b|\bone\s+focused\s+session\s+per\s+week\b", text):
        return 1, "Interpreted one focused session per week as one session weekly.", True
    if re.search(r"\b(?:twice\s+a\s+week|twice\s+weekly|deep work twice a week)\b", text):
        return 2, "Interpreted twice-weekly cadence as two sessions per week.", True
    if re.search(r"\b(?:daily|every school day|each school day)\b", text):
        return 5, "Interpreted daily school practice as five sessions per week.", False
    if re.search(r"\b(?:short frequent|frequent short|high-frequency short|bite-sized)\b", text):
        return 3, "Defaulted short frequent practice to three sessions per week.", False

    return None, None, False


def _infer_session_minutes(text: str, *, age_years: int | None) -> tuple[int | None, str | None, bool]:
    explicit = re.search(
        r"\b(\d{1,3})\s*(?:minutes?|mins?)\s+(?:per|each|a)\s+(?:session|lesson|day)\b",
        text,
        re.IGNORECASE,
    )
    if explicit:
        parsed = int(explicit.group(1))
        return parsed, f"Explicitly stated {parsed} minutes per session.", True

    capped = re.search(r"\bno more than\s+(\d{1,3})\s*(?:minutes?|mins?)\b", text, re.IGNORECASE)
    if capped:
        parsed = int(capped.group(1))
        return parsed, f"Used the stated session length cap of {parsed} minutes.", True

    if re.search(r"\b(?:short|brief|bite-sized|frequent)\b", text):
        if age_years is not None and age_years <= 6:
            return 10, "Defaulted short early-childhood sessions to 10 minutes.", False
        return 20, "Defaulted short sessions to 20 minutes.", False

    if re.search(r"\b(?:deep work|longer weekly|studio block)\b", text):
        return 45, "Defaulted deep-work sessions to 45 minutes.", False

    return None, None, False


def _enrich_planning_constraints(
    raw_artifact: dict[str, Any],
    payload: SourceInterpretationRequest,
) -> dict[str, Any]:
    artifact = dict(raw_artifact)
    constraints = dict(artifact.get("planningConstraints") or {})
    text = _source_text_for_pacing(payload, artifact)
    age_years = _infer_age_years(text)
    notes = [note for note in constraints.get("notes") or [] if isinstance(note, str)]

    def set_if_missing(key: str, value: int | str | None, note: str | None = None) -> None:
        if value is None or constraints.get(key) is not None:
            return
        constraints[key] = value
        if note and note not in notes:
            notes.append(note)

    total_sessions = _infer_total_sessions(text)
    if total_sessions is not None:
        set_if_missing("totalSessions", total_sessions, f"Detected explicit total session count: {total_sessions}.")

    total_weeks, weeks_note, weeks_explicit = _infer_total_weeks(text)
    sessions_per_week, sessions_note, sessions_explicit = _infer_sessions_per_week(text)
    session_minutes, minutes_note, _minutes_explicit = _infer_session_minutes(text, age_years=age_years)

    set_if_missing("totalWeeks", total_weeks, weeks_note)
    set_if_missing("sessionsPerWeek", sessions_per_week, sessions_note)
    set_if_missing("sessionMinutes", session_minutes, minutes_note)

    if (
        constraints.get("totalSessions") is None
        and total_weeks is not None
        and sessions_per_week is not None
        and weeks_explicit
        and sessions_explicit
    ):
        constraints["totalSessions"] = total_weeks * sessions_per_week
        notes.append(
            f"Computed totalSessions from explicit horizon and cadence: {total_weeks} weeks x {sessions_per_week} sessions per week."
        )

    if constraints.get("practiceCadence") is None:
        cadence = []
        if sessions_per_week is not None:
            cadence.append(f"{sessions_per_week} sessions per week")
        if session_minutes is not None:
            cadence.append(f"{session_minutes} minutes per session")
        if cadence:
            constraints["practiceCadence"] = ", ".join(cadence)

    if constraints != artifact.get("planningConstraints"):
        constraints["notes"] = notes
        artifact["planningConstraints"] = constraints
    return artifact


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

        repaired = _enrich_planning_constraints(raw_artifact, payload)
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

    def validate_artifact_semantics(self, *, artifact, payload, context) -> list[str]:
        enriched = _enrich_planning_constraints(
            artifact.model_dump(mode="json", exclude_none=True),
            payload,
        )
        if enriched != artifact.model_dump(mode="json", exclude_none=True):
            return ["planningConstraints missing inferable horizon or cadence defaults"]
        return []

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
