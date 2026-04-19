from __future__ import annotations

from learning_core.contracts.curriculum import (
    CurriculumArtifact,
    CurriculumLesson,
    CurriculumUnit,
    iter_document_skill_entries,
)
from learning_core.contracts.progression import (
    ProgressionGenerationRequest,
    ProgressionLaunchPlan,
    ProgressionLessonAnchor,
    ProgressionLessonType,
    ProgressionRevisionRequest,
    SkillCatalogItem,
)
from learning_core.contracts.source_interpret import SourceDeliveryPattern


def build_progression_request_from_curriculum(
    *,
    learner_name: str,
    source_title: str,
    source_summary: str | None,
    document,
    units: list[CurriculumUnit],
    launch_plan,
    request_mode: str | None,
    source_kind: str | None,
    delivery_pattern: SourceDeliveryPattern | None,
    entry_strategy: str | None,
    continuation_mode: str | None,
    revision_request: str | None = None,
) -> ProgressionGenerationRequest | ProgressionRevisionRequest:
    skill_catalog = _build_skill_catalog(document)
    lesson_anchors = _build_lesson_anchors(units)
    progression_launch_plan = _build_progression_launch_plan(launch_plan, lesson_anchors)
    common_kwargs = {
        "learnerName": learner_name,
        "sourceTitle": source_title,
        "sourceSummary": source_summary,
        "requestMode": request_mode,
        "sourceKind": source_kind,
        "deliveryPattern": delivery_pattern
        or _infer_delivery_pattern(lesson_anchors, progression_launch_plan),
        "entryStrategy": entry_strategy,
        "continuationMode": continuation_mode,
        "launchPlan": progression_launch_plan,
        "skillCatalog": skill_catalog,
        "lessonAnchors": lesson_anchors,
    }
    if revision_request is not None:
        return ProgressionRevisionRequest(
            **common_kwargs,
            revisionRequest=revision_request,
        )
    return ProgressionGenerationRequest(**common_kwargs)


def build_progression_request_from_artifact(
    artifact: CurriculumArtifact,
    *,
    learner_name: str,
    request_mode: str | None,
    source_kind: str | None,
    delivery_pattern: SourceDeliveryPattern | None,
    entry_strategy: str | None,
    continuation_mode: str | None,
    revision_request: str | None = None,
) -> ProgressionGenerationRequest | ProgressionRevisionRequest:
    return build_progression_request_from_curriculum(
        learner_name=learner_name,
        source_title=artifact.source.title,
        source_summary=artifact.source.summary,
        document=artifact.document,
        units=artifact.units,
        launch_plan=artifact.launchPlan,
        request_mode=request_mode,
        source_kind=source_kind,
        delivery_pattern=delivery_pattern,
        entry_strategy=entry_strategy,
        continuation_mode=continuation_mode,
        revision_request=revision_request,
    )


def _build_skill_catalog(document) -> list[SkillCatalogItem]:
    skill_catalog: list[SkillCatalogItem] = []
    for ordinal, (skill_ref, path, title) in enumerate(iter_document_skill_entries(document), start=1):
        skill_catalog.append(
            SkillCatalogItem(
                skillRef=skill_ref,
                title=title,
                domainTitle=path[0] if len(path) > 0 else None,
                strandTitle=path[1] if len(path) > 1 else None,
                goalGroupTitle=path[2] if len(path) > 2 else None,
                ordinal=ordinal,
            )
        )
    return skill_catalog


def _build_lesson_anchors(units: list[CurriculumUnit]) -> list[ProgressionLessonAnchor]:
    anchors: list[ProgressionLessonAnchor] = []
    order_index = 1
    for unit in units:
        for lesson in unit.lessons:
            anchors.append(
                ProgressionLessonAnchor(
                    lessonRef=lesson.lessonRef,
                    unitRef=lesson.unitRef,
                    title=lesson.title,
                    lessonType=lesson.lessonType,
                    orderIndex=order_index,
                    linkedSkillRefs=list(lesson.linkedSkillRefs),
                )
            )
            order_index += 1
    return anchors


def _build_progression_launch_plan(
    launch_plan,
    lesson_anchors: list[ProgressionLessonAnchor],
) -> ProgressionLaunchPlan:
    opening_lesson_refs = list(launch_plan.openingLessonRefs)
    opening_ref_set = set(opening_lesson_refs)
    opening_lessons = [anchor for anchor in lesson_anchors if anchor.lessonRef in opening_ref_set]

    opening_skill_refs = list(launch_plan.openingSkillRefs)
    if not opening_skill_refs:
        seen: set[str] = set()
        opening_skill_refs = []
        for anchor in opening_lessons:
            for skill_ref in anchor.linkedSkillRefs:
                if skill_ref not in seen:
                    opening_skill_refs.append(skill_ref)
                    seen.add(skill_ref)

    return ProgressionLaunchPlan(
        recommendedHorizon=launch_plan.recommendedHorizon,
        scopeSummary=launch_plan.scopeSummary,
        initialSliceUsed=launch_plan.initialSliceUsed,
        initialSliceLabel=launch_plan.initialSliceLabel,
        entryStrategy=launch_plan.entryStrategy,
        entryLabel=launch_plan.entryLabel,
        continuationMode=launch_plan.continuationMode,
        openingLessonRefs=opening_lesson_refs,
        openingSkillRefs=opening_skill_refs,
    )


def _infer_delivery_pattern(
    lesson_anchors: list[ProgressionLessonAnchor],
    launch_plan: ProgressionLaunchPlan,
) -> SourceDeliveryPattern:
    opening_ref_set = set(launch_plan.openingLessonRefs)
    opening_lessons = [anchor for anchor in lesson_anchors if anchor.lessonRef in opening_ref_set]
    if launch_plan.continuationMode == "timebox":
        return "timeboxed"
    if not opening_lessons:
        return "mixed"

    meaningful_types = [
        anchor.lessonType
        for anchor in opening_lessons
        if anchor.lessonType in {"task", "skill_support", "concept"}
    ]
    if not meaningful_types:
        return "mixed"

    unique_types = set(meaningful_types)
    if len(unique_types) > 1:
        return "mixed"

    first_type = meaningful_types[0]
    if first_type == "task":
        return "task_first"
    if first_type == "skill_support":
        return "skill_first"
    return "concept_first"


def _infer_lesson_type(lesson: CurriculumLesson) -> ProgressionLessonType:
    haystack = " ".join(
        [
            lesson.title,
            lesson.description,
            *lesson.objectives,
        ]
    ).lower()
    if _contains_keyword(haystack, ("setup", "set up", "orientation", "safety", "materials")):
        return "setup"
    if _contains_keyword(haystack, ("reflect", "reflection", "debrief", "journal")):
        return "reflection"
    if _contains_keyword(haystack, ("assessment", "quiz", "check for understanding", "demonstrate mastery")):
        return "assessment"
    if _contains_keyword(haystack, ("practice", "support", "scaffold", "guided", "reteach")):
        return "skill_support"
    if _contains_keyword(haystack, ("task", "project", "build", "create", "make", "challenge")):
        return "task"
    return "concept"


def _contains_keyword(haystack: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in haystack for keyword in keywords)
