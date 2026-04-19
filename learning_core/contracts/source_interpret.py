from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from learning_core.contracts.base import StrictModel


SourceInputModality = Literal["text", "outline", "photo", "image", "pdf", "file"]
SourceAssetExtractionStatus = Literal["pending", "ready", "requires_review", "failed"]
RequestedIntakeRoute = Literal["single_lesson", "weekly_plan", "outline", "topic", "manual_shell"]
SourceKind = Literal[
    "bounded_material",
    "timeboxed_plan",
    "structured_sequence",
    "comprehensive_source",
    "topic_seed",
    "shell_request",
    "ambiguous",
]
SourceEntryStrategy = Literal[
    "use_as_is",
    "explicit_range",
    "sequential_start",
    "section_start",
    "timebox_start",
    "scaffold_only",
]
SourceContinuationMode = Literal["none", "sequential", "timebox", "manual_review"]
SourceDeliveryPattern = Literal[
    "task_first",
    "skill_first",
    "concept_first",
    "timeboxed",
    "mixed",
]
SourceInterpretationHorizon = Literal[
    "single_day",
    "few_days",
    "one_week",
    "two_weeks",
    "starter_module",
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
    fileUrl: str | None = None
    fileData: str | None = None

    @model_validator(mode="after")
    def validate_reference(self) -> "SourceInputFile":
        if bool(self.fileUrl) == bool(self.fileData):
            raise ValueError("Provide exactly one of fileUrl or fileData.")
        return self


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
    titleCandidate: str | None = None


class SourceInterpretationArtifact(StrictModel):
    sourceKind: SourceKind
    entryStrategy: SourceEntryStrategy
    entryLabel: str | None = None
    continuationMode: SourceContinuationMode
    deliveryPattern: SourceDeliveryPattern
    suggestedTitle: str
    confidence: SourceInterpretationConfidence
    recommendedHorizon: SourceInterpretationHorizon
    assumptions: list[str]
    detectedChunks: list[str] = Field(min_length=1, max_length=20)
    followUpQuestion: str | None = None
    needsConfirmation: bool

    @model_validator(mode="after")
    def validate_confirmation_requirements(self) -> "SourceInterpretationArtifact":
        if self.followUpQuestion and not self.needsConfirmation:
            raise ValueError("needsConfirmation must be true when followUpQuestion is present.")
        if self.confidence == "low" and not self.needsConfirmation:
            raise ValueError("needsConfirmation must be true when confidence is low.")
        if self.sourceKind == "ambiguous" and not self.needsConfirmation:
            raise ValueError("needsConfirmation must be true when sourceKind is ambiguous.")
        return self
