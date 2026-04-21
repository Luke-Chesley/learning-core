from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from learning_core.contracts.activity import ActivityArtifact
from learning_core.contracts.curriculum import CurriculumArtifact
from learning_core.contracts.lesson_draft import StructuredLessonDraft
from learning_core.contracts.source_interpret import SourceInterpretationArtifact


ROOT = Path(__file__).parent
DEFAULT_CASES_PATH = ROOT / "fixtures" / "launch_eval" / "cases.json"
DEFAULT_RESULTS_TEMPLATE_PATH = ROOT / "fixtures" / "launch_eval" / "results_template.json"

HORIZON_ORDER = {
    "single_day": 0,
    "few_days": 1,
    "one_week": 2,
    "two_weeks": 3,
    "starter_module": 4,
}


class CurriculumRubric(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expectedDepth: str
    minUnits: int
    maxUnits: int
    minTotalWeeks: int | None = None
    maxTotalWeeks: int | None = None
    requiredKeywords: list[str] = Field(default_factory=list)


class LaunchHandoffRubric(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skipUntilConfirmation: bool
    chosenHorizon: str
    initialSliceUsed: bool
    openingLessonCountMin: int
    openingLessonCountMax: int
    scopeSummaryKeywords: list[str] = Field(default_factory=list)


class SessionActivityRubric(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skipUntilConfirmation: bool
    maxLessonMinutes: int
    maxActivityMinutes: int
    requiredKeywords: list[str] = Field(default_factory=list)
    allowOfflineActivity: bool


class CopilotRubric(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str
    allowedActionKinds: list[str] = Field(default_factory=list)
    maxActionCount: int
    requiresApprovalForActions: bool
    shouldPreferNoAction: bool


class LaunchEvalCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    sourceClass: str
    sourceInterpretInput: dict[str, Any]
    expectedSourceInterpretArtifact: dict[str, Any]
    curriculumGenerateInput: dict[str, Any] | None = None
    curriculumRubric: CurriculumRubric
    launchHandoffRubric: LaunchHandoffRubric
    sessionActivityRubric: SessionActivityRubric
    copilotRubric: CopilotRubric


class LaunchEvalCorpus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int
    supportedCopilotActionKinds: list[str]
    cases: list[LaunchEvalCase]


class CopilotActionCapture(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    kind: str
    label: str
    description: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    requiresApproval: bool | None = None
    confidence: float | str | None = None
    rationale: str | None = None


class CopilotArtifactCapture(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str
    actions: list[CopilotActionCapture] = Field(default_factory=list)


class LaunchHandoffCapture(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chosenHorizon: str
    scopeSummary: str
    initialSliceUsed: bool
    initialSliceLabel: str | None = None
    openingLessonCount: int | None = None
    openingLessonTitles: list[str] = Field(default_factory=list)


class CapturedCaseResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    caseId: str
    sourceInterpretArtifact: dict[str, Any] | None = None
    curriculumArtifact: dict[str, Any] | None = None
    launchHandoff: LaunchHandoffCapture | None = None
    sessionArtifact: dict[str, Any] | None = None
    activityArtifact: dict[str, Any] | None = None
    copilotArtifact: CopilotArtifactCapture | None = None
    notes: list[str] = Field(default_factory=list)


class CapturedResults(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capturedAt: str
    runLabel: str
    environment: str
    cases: list[CapturedCaseResult] = Field(default_factory=list)


def load_corpus(path: Path) -> LaunchEvalCorpus:
    return LaunchEvalCorpus.model_validate(json.loads(path.read_text(encoding="utf-8")))


def count_keyword_hits(text: str, keywords: list[str]) -> int:
    haystack = text.lower()
    return sum(1 for keyword in keywords if keyword.lower() in haystack)


def curriculum_text(artifact: CurriculumArtifact) -> str:
    parts = [
        artifact.source.title,
        artifact.source.description,
        artifact.source.summary,
        artifact.source.teachingApproach,
        artifact.intakeSummary,
        artifact.pacing.coverageStrategy,
        *artifact.pacing.coverageNotes,
    ]
    for unit in artifact.units:
        parts.extend([unit.title, unit.description])
    return " ".join(part for part in parts if part)


def lesson_text(artifact: StructuredLessonDraft) -> str:
    parts = [
        artifact.title,
        artifact.lesson_focus,
        *artifact.primary_objectives,
        *artifact.success_criteria,
        *artifact.teacher_notes,
        *artifact.materials,
        *(block.title for block in artifact.blocks),
        *(block.purpose for block in artifact.blocks),
        *(block.teacher_action for block in artifact.blocks),
        *(block.learner_action for block in artifact.blocks),
    ]
    return " ".join(part for part in parts if part)


def activity_text(artifact: ActivityArtifact) -> str:
    parts = [artifact.title, artifact.purpose, *artifact.linkedSkillLabels]
    for component in artifact.components:
        component_data = component.model_dump(mode="json")
        for key in ("text", "prompt", "caption", "instruction", "instructionText"):
            value = component_data.get(key)
            if isinstance(value, str):
                parts.append(value)
    return " ".join(part for part in parts if part)


def score_source_interpret(
    case: LaunchEvalCase, capture: CapturedCaseResult
) -> tuple[int | None, list[str], list[str]]:
    if capture.sourceInterpretArtifact is None:
        return None, ["missing source_interpret artifact"], []

    warnings: list[str] = []
    blockers: list[str] = []
    expected = SourceInterpretationArtifact.model_validate(case.expectedSourceInterpretArtifact)
    try:
        actual = SourceInterpretationArtifact.model_validate(capture.sourceInterpretArtifact)
    except ValidationError as exc:
        return 0, [], [f"invalid source_interpret artifact: {exc.errors()[0]['msg']}"]

    score = 3
    for label, expected_value, actual_value in (
        ("sourceKind", expected.sourceKind, actual.sourceKind),
        ("entryStrategy", expected.entryStrategy, actual.entryStrategy),
        ("continuationMode", expected.continuationMode, actual.continuationMode),
        ("deliveryPattern", expected.deliveryPattern, actual.deliveryPattern),
    ):
        if expected_value != actual_value:
            score -= 1
            warnings.append(f"{label} expected {expected_value} but got {actual_value}")

    if expected.needsConfirmation != actual.needsConfirmation:
        score -= 1
        warnings.append(
            f"needsConfirmation expected {expected.needsConfirmation} but got {actual.needsConfirmation}"
        )

    horizon_distance = abs(
        HORIZON_ORDER[expected.recommendedHorizon] - HORIZON_ORDER[actual.recommendedHorizon]
    )
    if horizon_distance:
        score -= min(horizon_distance, 2)
        warnings.append(
            f"recommendedHorizon expected {expected.recommendedHorizon} but got {actual.recommendedHorizon}"
        )

    if expected.needsConfirmation and actual.followUpQuestion is None:
        blockers.append("ambiguous source must include a follow-up question")
    if not actual.assumptions:
        warnings.append("source_interpret assumptions are empty")
    if not actual.detectedChunks:
        blockers.append("source_interpret detectedChunks must not be empty")

    return max(score, 0), warnings, blockers


def score_curriculum(
    case: LaunchEvalCase, capture: CapturedCaseResult
) -> tuple[int | None, list[str], list[str]]:
    rubric = case.curriculumRubric
    if rubric.expectedDepth == "skip_until_confirmation":
        if capture.curriculumArtifact is None:
            return None, [], []
        return 0, [], ["curriculum artifact should be omitted until confirmation is resolved"]

    if capture.curriculumArtifact is None:
        return None, ["missing curriculum artifact"], []

    warnings: list[str] = []
    blockers: list[str] = []
    try:
        artifact = CurriculumArtifact.model_validate(capture.curriculumArtifact)
    except ValidationError as exc:
        return 0, [], [f"invalid curriculum artifact: {exc.errors()[0]['msg']}"]

    score = 3
    unit_count = len(artifact.units)
    if not rubric.minUnits <= unit_count <= rubric.maxUnits:
        score -= 1
        warnings.append(
            f"unit count expected {rubric.minUnits}-{rubric.maxUnits} but got {unit_count}"
        )

    total_weeks = artifact.pacing.totalWeeks
    if rubric.minTotalWeeks is not None and (total_weeks or 0) < rubric.minTotalWeeks:
        score -= 1
        warnings.append(f"totalWeeks expected >= {rubric.minTotalWeeks} but got {total_weeks}")
    if rubric.maxTotalWeeks is not None and total_weeks is not None and total_weeks > rubric.maxTotalWeeks:
        score -= 1
        warnings.append(f"totalWeeks expected <= {rubric.maxTotalWeeks} but got {total_weeks}")

    keyword_hits = count_keyword_hits(curriculum_text(artifact), rubric.requiredKeywords)
    if rubric.requiredKeywords and keyword_hits == 0:
        score -= 1
        warnings.append("curriculum artifact does not mention any required source keywords")

    durable_signal = unit_count >= 2 or (artifact.pacing.totalSessions or 0) >= 6
    if rubric.expectedDepth == "durable" and not durable_signal:
        blockers.append("durable source did not produce a durable curriculum signal")
    if rubric.expectedDepth == "bounded" and unit_count > 2:
        blockers.append("bounded source expanded beyond a bounded curriculum")

    return max(score, 0), warnings, blockers


def score_launch_handoff(
    case: LaunchEvalCase, capture: CapturedCaseResult
) -> tuple[int | None, list[str], list[str]]:
    rubric = case.launchHandoffRubric
    if rubric.skipUntilConfirmation:
        if capture.launchHandoff is None:
            return None, [], []
        return 0, [], ["launch handoff should be omitted until confirmation is resolved"]

    if capture.launchHandoff is None:
        return None, ["missing launch handoff capture"], []

    warnings: list[str] = []
    blockers: list[str] = []
    handoff = capture.launchHandoff
    score = 3

    if handoff.chosenHorizon != rubric.chosenHorizon:
        score -= 1
        warnings.append(
            f"chosenHorizon expected {rubric.chosenHorizon} but got {handoff.chosenHorizon}"
        )
    if handoff.initialSliceUsed != rubric.initialSliceUsed:
        score -= 1
        warnings.append(
            f"initialSliceUsed expected {rubric.initialSliceUsed} but got {handoff.initialSliceUsed}"
        )

    if handoff.openingLessonCount is None:
        score -= 1
        warnings.append("openingLessonCount is missing")
    elif not rubric.openingLessonCountMin <= handoff.openingLessonCount <= rubric.openingLessonCountMax:
        score -= 1
        warnings.append(
            f"openingLessonCount expected {rubric.openingLessonCountMin}-{rubric.openingLessonCountMax} but got {handoff.openingLessonCount}"
        )

    keyword_hits = count_keyword_hits(handoff.scopeSummary, rubric.scopeSummaryKeywords)
    if rubric.scopeSummaryKeywords and keyword_hits == 0:
        score -= 1
        warnings.append("scopeSummary is missing the expected opening-window terms")

    if not handoff.scopeSummary.strip():
        blockers.append("launch handoff scopeSummary must not be empty")

    return max(score, 0), warnings, blockers


def score_session_activity(
    case: LaunchEvalCase, capture: CapturedCaseResult
) -> tuple[int | None, list[str], list[str]]:
    rubric = case.sessionActivityRubric
    if rubric.skipUntilConfirmation:
        if capture.sessionArtifact is None and capture.activityArtifact is None:
            return None, [], []
        return 0, [], ["session/activity artifacts should be omitted until confirmation is resolved"]

    if capture.sessionArtifact is None or capture.activityArtifact is None:
        return None, ["missing lesson or activity artifact"], []

    warnings: list[str] = []
    blockers: list[str] = []
    try:
        lesson = StructuredLessonDraft.model_validate(capture.sessionArtifact)
    except ValidationError as exc:
        return 0, [], [f"invalid lesson artifact: {exc.errors()[0]['msg']}"]

    try:
        activity = ActivityArtifact.model_validate(capture.activityArtifact)
    except ValidationError as exc:
        return 0, [], [f"invalid activity artifact: {exc.errors()[0]['msg']}"]

    score = 3
    if lesson.total_minutes > rubric.maxLessonMinutes:
        score -= 1
        warnings.append(
            f"lesson total_minutes expected <= {rubric.maxLessonMinutes} but got {lesson.total_minutes}"
        )
    if activity.estimatedMinutes > rubric.maxActivityMinutes:
        score -= 1
        warnings.append(
            f"activity estimatedMinutes expected <= {rubric.maxActivityMinutes} but got {activity.estimatedMinutes}"
        )
    if not rubric.allowOfflineActivity and activity.interactionMode == "offline":
        score -= 1
        warnings.append("activity fell back to offline when a digital or hybrid activity was expected")

    keyword_hits = count_keyword_hits(
        f"{lesson_text(lesson)} {activity_text(activity)}",
        rubric.requiredKeywords,
    )
    if rubric.requiredKeywords and keyword_hits == 0:
        score -= 1
        warnings.append("lesson/activity pair is missing the expected source grounding keywords")

    if not lesson.blocks:
        blockers.append("lesson artifact must include at least one block")
    if not activity.components:
        blockers.append("activity artifact must include at least one component")

    return max(score, 0), warnings, blockers


def score_copilot(
    case: LaunchEvalCase,
    capture: CapturedCaseResult,
    supported_action_kinds: set[str],
) -> tuple[int | None, list[str], list[str]]:
    if capture.copilotArtifact is None:
        return None, ["missing copilot artifact"], []

    warnings: list[str] = []
    blockers: list[str] = []
    rubric = case.copilotRubric
    artifact = capture.copilotArtifact
    actions = artifact.actions

    if not artifact.answer.strip():
        return 0, [], ["copilot answer must not be empty"]

    score = 3
    if len(actions) > rubric.maxActionCount:
        score -= 1
        warnings.append(f"action count expected <= {rubric.maxActionCount} but got {len(actions)}")
    if rubric.shouldPreferNoAction and actions:
        score -= 2
        blockers.append("copilot proposed actions for a case that should prefer no action")
    if not rubric.shouldPreferNoAction and not actions:
        score -= 1
        warnings.append("copilot returned no actions for a case that likely benefits from one")

    for action in actions:
        if action.kind not in supported_action_kinds:
            blockers.append(f"unsupported action kind: {action.kind}")
        if action.kind not in rubric.allowedActionKinds:
            score -= 1
            warnings.append(f"action kind {action.kind} is outside the fixture allowlist")
        if rubric.requiresApprovalForActions and action.requiresApproval is not True:
            blockers.append(f"action {action.id} is missing requiresApproval=true")
        if not action.label.strip():
            blockers.append(f"action {action.id} is missing a label")

    return max(score, 0), warnings, blockers


def average(values: list[int]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def build_corpus_summary(corpus: LaunchEvalCorpus) -> dict[str, Any]:
    return {
        "version": corpus.version,
        "fixtureCount": len(corpus.cases),
        "sourceClasses": [case.sourceClass for case in corpus.cases],
        "supportedCopilotActionKinds": corpus.supportedCopilotActionKinds,
        "coverageComplete": len(corpus.cases) >= 10,
        "resultsTemplatePath": str(DEFAULT_RESULTS_TEMPLATE_PATH),
    }


def score_results(corpus: LaunchEvalCorpus, results: CapturedResults) -> dict[str, Any]:
    case_map = {case.id: case for case in corpus.cases}
    provided = {case.caseId: case for case in results.cases}
    supported_action_kinds = set(corpus.supportedCopilotActionKinds)
    stage_scores: dict[str, list[int]] = {
        "source_interpret": [],
        "curriculum_generate": [],
        "launch_handoff": [],
        "session_activity": [],
        "copilot": [],
    }
    warnings: list[str] = []
    blockers: list[str] = []
    per_case: list[dict[str, Any]] = []

    for fixture_case in corpus.cases:
        capture = provided.get(fixture_case.id, CapturedCaseResult(caseId=fixture_case.id))
        case_warnings: list[str] = []
        case_blockers: list[str] = []

        scores = {
            "source_interpret": score_source_interpret(fixture_case, capture),
            "curriculum_generate": score_curriculum(fixture_case, capture),
            "launch_handoff": score_launch_handoff(fixture_case, capture),
            "session_activity": score_session_activity(fixture_case, capture),
            "copilot": score_copilot(fixture_case, capture, supported_action_kinds),
        }

        for stage_name, (score, stage_warnings, stage_blockers) in scores.items():
            if score is not None:
                stage_scores[stage_name].append(score)
            case_warnings.extend(stage_warnings)
            case_blockers.extend(stage_blockers)

        if fixture_case.id not in provided:
            warnings.append(f"{fixture_case.id}: no captured results provided")

        warnings.extend(f"{fixture_case.id}: {item}" for item in case_warnings)
        blockers.extend(f"{fixture_case.id}: {item}" for item in case_blockers)

        per_case.append(
            {
                "caseId": fixture_case.id,
                "label": fixture_case.label,
                "scores": {stage_name: stage_result[0] for stage_name, stage_result in scores.items()},
                "warnings": case_warnings,
                "blockers": case_blockers,
            }
        )

    averages = {stage_name: average(values) for stage_name, values in stage_scores.items()}
    ready = not blockers and all(
        value is not None and value >= threshold
        for value, threshold in (
            (averages["source_interpret"], 2.5),
            (averages["curriculum_generate"], 2.25),
            (averages["launch_handoff"], 2.25),
            (averages["session_activity"], 2.0),
            (averages["copilot"], 2.0),
        )
    )

    return {
        "capturedAt": results.capturedAt,
        "runLabel": results.runLabel,
        "environment": results.environment,
        "fixtureCount": len(case_map),
        "casesProvided": len(results.cases),
        "averages": averages,
        "warnings": warnings,
        "blockers": blockers,
        "ready": ready,
        "perCase": per_case,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score launch-eval fixtures and captured outputs.")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES_PATH)
    parser.add_argument("--results", type=Path)
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    corpus = load_corpus(args.cases)
    if args.results is None:
        payload = build_corpus_summary(corpus)
    else:
        results = CapturedResults.model_validate(json.loads(args.results.read_text(encoding="utf-8")))
        payload = score_results(corpus, results)

    print(json.dumps(payload, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
