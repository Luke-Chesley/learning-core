from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, runtime_checkable

from langchain_core.tools import BaseTool

from learning_core.contracts.activity import ActivityArtifact
from learning_core.runtime.context import RuntimeContext
from learning_core.runtime.providers import ModelRuntime
from learning_core.skills.activity_generate.scripts.schemas import ActivityGenerationInput


@dataclass(frozen=True)
class PackPlanningResult:
    """Pack-local planning output that can feed final composition and validation."""

    pack_name: str
    prompt_sections: tuple[str, ...] = ()
    structured_data: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PackValidationContext:
    """Runtime validation context, including any pack planning outputs."""

    planning_result: PackPlanningResult | None = None


@runtime_checkable
class Pack(Protocol):
    """A subject pack that owns keywords, prompt docs, tools, validators, and UI specs for activity_generate."""

    @property
    def name(self) -> str: ...

    @property
    def keywords(self) -> tuple[str, ...]: ...

    def prompt_sections(self) -> list[str]:
        """Return markdown doc sections to append to the user prompt when this pack is active."""
        ...

    def needs_planning(self, payload: ActivityGenerationInput, context: RuntimeContext) -> bool:
        """Return whether this pack should run a pack-local planning phase for the request."""
        ...

    def run_planning_phase(
        self,
        payload: ActivityGenerationInput,
        context: RuntimeContext,
        model_runtime: ModelRuntime,
    ) -> PackPlanningResult | None:
        """Run an optional pack-local planning phase before final artifact composition."""
        ...

    def tools(self) -> list[BaseTool]:
        """Return LangChain tools this pack exposes to the agent loop."""
        ...

    def auto_injected_ui_specs(self) -> list[str]:
        """Return UI spec doc paths to auto-inject into the prompt when this pack is active.

        These are injected automatically so the model does not need to read them via tools.
        Paths are relative to the skill dir, e.g. 'ui_components/interactive_widget.md'.
        """
        ...

    def validators(self) -> list[PackValidator]:
        """Return pack-specific validators to run post-generation."""
        ...

    def required_tool_names(self) -> list[str]:
        """Return tool names that must be used when the artifact contains pack-specific widgets.

        If the generated artifact contains widgets owned by this pack but none of
        these tools were called, a targeted repair pass is triggered.
        """
        ...

    def repair_guidance(self) -> str | None:
        """Return optional repair guidance text for the repair prompt when pack tool use was missing."""
        ...

    def detect_pack_widgets(self, artifact: ActivityArtifact) -> list[str]:
        """Return component IDs of widgets in the artifact that belong to this pack."""
        ...


class PackValidator:
    """A pack-owned validator that checks and optionally normalizes an artifact."""

    def normalize_and_validate(
        self,
        artifact: ActivityArtifact,
        validation_context: PackValidationContext | None = None,
    ) -> tuple[ActivityArtifact, list[str], list[str]]:
        """Validate and normalize an artifact.

        Returns:
            (normalized_artifact, hard_errors, soft_warnings)
        """
        raise NotImplementedError
