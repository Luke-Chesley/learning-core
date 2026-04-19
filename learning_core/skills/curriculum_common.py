from __future__ import annotations

from learning_core.contracts.curriculum import CurriculumArtifact, CurriculumUnit, iter_document_skill_entries
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
    document,
    units: list[CurriculumUnit],
    request_mode: str | None,
    source_kind: str | None,
    delivery_pattern: SourceDeliveryPattern | None,
    entry_strategy: str | None,
    continuation_mode: str | None,
    revision_request: str | None = None,
) -> ProgressionGenerationRequest | ProgressionRevisionRequest:
    skill_catalog = build_skill_catalog(document)
    unit_anchors = build_unit_anchors(units)
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
        document=artifact.document,
        units=artifact.units,
        request_mode=request_mode,
        source_kind=source_kind,
        delivery_pattern=delivery_pattern,
        entry_strategy=entry_strategy,
        continuation_mode=continuation_mode,
        revision_request=revision_request,
    )


def build_skill_catalog(document) -> list[SkillCatalogItem]:
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


def build_unit_anchors(units: list[CurriculumUnit]) -> list[ProgressionUnitAnchor]:
    anchors: list[ProgressionUnitAnchor] = []
    for index, unit in enumerate(units, start=1):
        anchors.append(
            ProgressionUnitAnchor(
                unitRef=unit.unitRef,
                title=unit.title,
                description=unit.description,
                orderIndex=index,
                estimatedWeeks=unit.estimatedWeeks,
                estimatedSessions=unit.estimatedSessions,
                skillRefs=list(unit.skillRefs),
            )
        )
    return anchors
