from __future__ import annotations

import json
from pathlib import Path

from langchain_core.tools import BaseTool

from learning_core.contracts.activity import ActivityArtifact
from learning_core.runtime.context import RuntimeContext
from learning_core.runtime.providers import ModelRuntime
from learning_core.skills.activity_generate.packs.base import PackPlanningResult, PackValidator
from learning_core.skills.activity_generate.packs.geography.tools import GEOGRAPHY_TOOLS
from learning_core.skills.activity_generate.packs.geography.validation import GeographyValidator
from learning_core.skills.activity_generate.scripts.schemas import ActivityGenerationInput

_PACK_DIR = Path(__file__).resolve().parent
_DOC_FILENAMES = ("pack.md", "patterns.md", "examples.md")

_KEYWORDS: tuple[str, ...] = (
    "geography",
    "map",
    "maps",
    "continent",
    "country",
    "countries",
    "state",
    "states",
    "capital",
    "river",
    "mountain",
    "empire",
    "trade route",
    "migration",
    "historical map",
    "timeline map",
    "atlas",
    "region",
    "border",
)

_AUTO_INJECTED_UI_SPECS: list[str] = [
    "ui_components/interactive_widget.md",
    "ui_widgets/map_surface__geojson.md",
]

_REQUIRED_TOOL_NAMES: list[str] = [
    "map_build_widget_config",
    "map_validate_widget_config",
]

_REPAIR_GUIDANCE = (
    "The activity contains map widgets but no geography validation tools were used during generation. "
    "Before finalizing, validate each map widget with map_validate_widget_config. "
    "When building new map activities, prefer source-backed map_build_widget_config and source inspection tools over hand-authoring geometry. "
    "Do not invent sourceId values, layer ids, or feature ids. Use map_describe_source, map_lookup_feature, and map_build_widget_config to get canonical source-backed values first."
)


class GeographyPack:
    @property
    def name(self) -> str:
        return "geography"

    @property
    def keywords(self) -> tuple[str, ...]:
        return _KEYWORDS

    def prompt_sections(self) -> list[str]:
        return [(_PACK_DIR / filename).read_text(encoding="utf-8").strip() for filename in _DOC_FILENAMES]

    def needs_planning(self, payload: ActivityGenerationInput, context: RuntimeContext) -> bool:
        text = " ".join(
            value.lower()
            for value in [
                payload.subject or "",
                payload.lesson_draft.title,
                payload.lesson_draft.lesson_focus,
                " ".join(payload.linked_skill_titles),
            ]
            if value
        )
        return any(keyword in text for keyword in ("map", "route", "timeline", "empire", "migration", "compare"))

    def run_planning_phase(
        self,
        payload: ActivityGenerationInput,
        context: RuntimeContext,
        model_runtime: ModelRuntime,
    ) -> PackPlanningResult | None:
        lesson = payload.lesson_draft
        lines = [
            f"Lesson title: {lesson.title}",
            f"Lesson focus: {lesson.lesson_focus}",
            "Create a concise planning brief for a map-centered lesson artifact.",
            "Return JSON with keys: recommendedSourceId, recommendedInteractionMode, teachingArtifactMode, suggestedFeatureIds, rationale, compareSourceId.",
        ]
        response = model_runtime.client.invoke("\n".join(lines))
        try:
            content = getattr(response, "content", response)
            if isinstance(content, list):
                content = "\n".join(
                    part.get("text", "") if isinstance(part, dict) else str(part)
                    for part in content
                )
            structured_data = json.loads(content if isinstance(content, str) else str(content))
            return PackPlanningResult(
                pack_name=self.name,
                prompt_sections=(),
                structured_data={
                    "phase": "geography_map_planning",
                    "plan": structured_data,
                },
            )
        except Exception:
            return PackPlanningResult(
                pack_name=self.name,
                prompt_sections=(),
                structured_data={
                    "phase": "geography_map_planning",
                    "plan": {
                        "recommendedSourceId": "geoboundaries:USA:ADM1",
                        "recommendedInteractionMode": "guided_explore",
                        "teachingArtifactMode": True,
                        "suggestedFeatureIds": [],
                        "rationale": "Fallback planning result when structured parsing failed.",
                        "compareSourceId": None,
                    },
                },
            )

    def tools(self) -> list[BaseTool]:
        return list(GEOGRAPHY_TOOLS)

    def auto_injected_ui_specs(self) -> list[str]:
        return list(_AUTO_INJECTED_UI_SPECS)

    def validators(self) -> list[PackValidator]:
        return [GeographyValidator()]

    def required_tool_names(self) -> list[str]:
        return list(_REQUIRED_TOOL_NAMES)

    def repair_guidance(self) -> str | None:
        return _REPAIR_GUIDANCE

    def detect_pack_widgets(self, artifact: ActivityArtifact) -> list[str]:
        return [
            component.id
            for component in artifact.components
            if component.type == "interactive_widget" and component.widget.engineKind == "map_geojson"
        ]
