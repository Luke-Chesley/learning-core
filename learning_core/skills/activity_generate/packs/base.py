from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from langchain_core.tools import BaseTool

from learning_core.contracts.activity import ActivityArtifact


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
    ) -> tuple[ActivityArtifact, list[str], list[str]]:
        """Validate and normalize an artifact.

        Returns:
            (normalized_artifact, hard_errors, soft_warnings)
        """
        raise NotImplementedError
