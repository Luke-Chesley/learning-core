from __future__ import annotations

import re

from learning_core.contracts.activity import ActivityArtifact, InteractiveWidgetComponent
from learning_core.contracts.widgets import MapGeoJsonWidget
from learning_core.skills.activity_generate.packs.base import PackValidationContext, PackValidator
from learning_core.skills.activity_generate.packs.geography.engine import validate_widget_config

_MAP_CENTERED_PATTERNS = (
    re.compile(r"\bmap\b", re.IGNORECASE),
    re.compile(r"\btrace\b", re.IGNORECASE),
    re.compile(r"\broute\b", re.IGNORECASE),
    re.compile(r"\blocate\b", re.IGNORECASE),
    re.compile(r"\bcompare\b", re.IGNORECASE),
    re.compile(r"\bregion\b", re.IGNORECASE),
)


def _visible_text(component: InteractiveWidgetComponent, widget: MapGeoJsonWidget) -> str:
    return " ".join(
        value.strip()
        for value in [component.prompt or "", widget.instructionText or "", widget.caption or ""]
        if value and value.strip()
    )


def validate_map_widget(
    artifact: ActivityArtifact,
    component: InteractiveWidgetComponent,
    widget: MapGeoJsonWidget,
) -> tuple[list[str], list[str]]:
    hard_errors: list[str] = []
    soft_warnings: list[str] = []
    raw = widget.model_dump(mode="json", exclude_none=True)
    config_report = validate_widget_config(raw)
    hard_errors.extend(
        f'Interactive widget "{component.id}" {message[0].lower()}{message[1:]}'
        for message in config_report["errors"]
    )
    soft_warnings.extend(
        f'Interactive widget "{component.id}" {message[0].lower()}{message[1:]}'
        for message in config_report["warnings"]
    )

    prompt = _visible_text(component, widget)
    mode = widget.interaction.mode

    if mode in {"select_region", "multi_select_regions", "place_marker", "trace_path", "label_regions"}:
        if widget.display.surfaceRole != "primary":
            soft_warnings.append(
                f'Interactive widget "{component.id}" accepts map input but display.surfaceRole is not "primary".'
            )

    if mode in {"guided_explore", "compare_layers", "timeline_scrub"} and component.required:
        soft_warnings.append(
            f'Interactive widget "{component.id}" is a teaching artifact mode and usually should not be required.'
        )

    if any(pattern.search(prompt) for pattern in _MAP_CENTERED_PATTERNS):
        if widget.display.surfaceRole != "primary" and mode not in {"guided_explore", "compare_layers", "timeline_scrub"}:
            soft_warnings.append(
                f'Interactive widget "{component.id}" appears in a map-centered context but is not marked primary.'
            )

    if mode == "compare_layers" and len(widget.layers) < 2:
        hard_errors.append(
            f'Interactive widget "{component.id}" uses compare_layers but does not define at least two layers.'
        )

    return hard_errors, soft_warnings


class GeographyValidator(PackValidator):
    def normalize_and_validate(
        self,
        artifact: ActivityArtifact,
        validation_context: PackValidationContext | None = None,
    ) -> tuple[ActivityArtifact, list[str], list[str]]:
        normalized = artifact.model_copy(deep=True)
        hard_errors: list[str] = []
        soft_warnings: list[str] = []

        for component in normalized.components:
            if component.type != "interactive_widget" or component.widget.engineKind != "map_geojson":
                continue
            widget_hard, widget_soft = validate_map_widget(normalized, component, component.widget)
            hard_errors.extend(widget_hard)
            soft_warnings.extend(widget_soft)

        return normalized, hard_errors, soft_warnings
