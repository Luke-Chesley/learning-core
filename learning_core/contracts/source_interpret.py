from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from learning_core.contracts.base import StrictModel


SourceInputModality = Literal["text", "outline", "photo", "image", "pdf", "file"]
SourceAssetExtractionStatus = Literal["pending", "ready", "requires_review", "failed"]
RequestedIntakeRoute = Literal["single_lesson", "weekly_plan", "outline", "topic", "manual_shell"]
UserHorizonIntent = Literal["today_only", "auto"]
SourceKind = Literal[
    "single_day_material",
    "weekly_assignments",
    "sequence_outline",
    "topic_seed",
    "manual_shell",
    "ambiguous",
]
SourceInterpretationHorizon = Literal[
    "today",
    "tomorrow",
    "next_few_days",
    "current_week",
    "starter_module",
    "starter_week",
]
SourceInterpretationConfidence = Literal["low", "medium", "high"]


class SourcePackageContext(StrictModel):
    id: str
    title: str
    modality: SourceInputModality
    summary: str
    extractionStatus: SourceAssetExtractionStatus
    assetCount: int = 0
    assetIds: list[str] = Field(default_factory=list)
    detectedChunks: list[str] = Field(default_factory=list)
    sourceFingerprint: str | None = None


class SourceInputFile(StrictModel):
    assetId: str
    packageId: str
    title: str
    modality: SourceInputModality
    fileName: str
    mimeType: str
    fileUrl: str


class SourceInterpretationRequest(StrictModel):
    learnerName: str | None = None
    requestedRoute: RequestedIntakeRoute
    inputModalities: list[SourceInputModality] = Field(default_factory=list)
    rawText: str | None = None
    extractedText: str = Field(min_length=1)
    extractedStructure: dict[str, Any] | None = None
    assetRefs: list[str] = Field(default_factory=list)
    sourcePackages: list[SourcePackageContext] = Field(default_factory=list)
    sourceFiles: list[SourceInputFile] = Field(default_factory=list)
    userHorizonIntent: UserHorizonIntent = "auto"
    titleCandidate: str | None = None


class SourceInterpretationArtifact(StrictModel):
    sourceKind: SourceKind
    suggestedTitle: str
    confidence: SourceInterpretationConfidence
    recommendedHorizon: SourceInterpretationHorizon
    assumptions: list[str] = Field(default_factory=list)
    detectedChunks: list[str] = Field(default_factory=list)
    followUpQuestion: str | None = None
    needsConfirmation: bool = False
