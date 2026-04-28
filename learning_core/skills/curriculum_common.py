from __future__ import annotations

from learning_core.contracts.curriculum import CurriculumArtifact, CurriculumSkill, CurriculumUnit
from learning_core.contracts.progression import (
    ProgressionGenerationRequest,
    ProgressionRevisionRequest,
    ProgressionUnitAnchor,
    SkillCatalogItem,
)
from learning_core.contracts.source_interpret import SourceDeliveryPattern


def build_progression_request_from_curriculum(
    *,
    learner_name: str,
    source_title: str,
    source_summary: str | None,
    skills: list[CurriculumSkill],
    units: list[CurriculumUnit],
    request_mode: str | None,
    source_kind: str | None,
    delivery_pattern: SourceDeliveryPattern | None,
    entry_strategy: str | None,
    continuation_mode: str | None,
    revision_request: str | None = None,
) -> ProgressionGenerationRequest | ProgressionRevisionRequest:
    skill_catalog = build_skill_catalog(skills)
    unit_anchors = build_unit_anchors(units, skills)
    common_kwargs = {
        "learnerName": learner_name,
        "sourceTitle": source_title,
        "sourceSummary": source_summary,
        "requestMode": request_mode,
        "sourceKind": source_kind,
        "deliveryPattern": delivery_pattern,
        "entryStrategy": entry_strategy,
        "continuationMode": continuation_mode,
        "skillCatalog": skill_catalog,
        "unitAnchors": unit_anchors,
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
        skills=artifact.skills,
        units=artifact.units,
        request_mode=request_mode,
        source_kind=source_kind,
        delivery_pattern=delivery_pattern,
        entry_strategy=entry_strategy,
        continuation_mode=continuation_mode,
        revision_request=revision_request,
    )


def build_skill_catalog(skills: list[CurriculumSkill]) -> list[SkillCatalogItem]:
    skill_catalog: list[SkillCatalogItem] = []
    for ordinal, skill in enumerate(skills, start=1):
        skill_catalog.append(
            SkillCatalogItem(
                skillRef=skill.canonical_skill_ref(),
                title=skill.title,
                description=skill.description,
                domainTitle=skill.domainTitle,
                strandTitle=skill.strandTitle,
                goalGroupTitle=skill.goalGroupTitle,
                ordinal=ordinal,
                contentAnchors=skill.contentAnchorIds,
                assessmentCue=skill.assessmentCue,
            )
        )
    return skill_catalog


def build_unit_anchors(
    units: list[CurriculumUnit],
    skills: list[CurriculumSkill],
) -> list[ProgressionUnitAnchor]:
    skill_ref_by_id = {
        skill.skillId: skill.canonical_skill_ref()
        for skill in skills
    }

    anchors: list[ProgressionUnitAnchor] = []
    for index, unit in enumerate(units, start=1):
        skill_refs = [skill_ref_by_id.get(skill_id, skill_id) for skill_id in unit.skillIds]
        anchors.append(
            ProgressionUnitAnchor(
                unitRef=unit.unitRef,
                title=unit.title,
                description=unit.description,
                orderIndex=index,
                estimatedWeeks=unit.estimatedWeeks,
                estimatedSessions=unit.estimatedSessions,
                skillRefs=skill_refs,
            )
        )
    return anchors
