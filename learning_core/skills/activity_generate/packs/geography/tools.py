from __future__ import annotations

import json

from langchain_core.tools import BaseTool, tool

from learning_core.skills.activity_generate.packs.geography.engine import (
    build_widget_config,
    describe_source,
    evaluate_feature_selection,
    evaluate_labels,
    evaluate_marker,
    evaluate_path,
    fetch_source_collection,
    feature_by_id,
    geocode_place,
    generate_guided_artifact,
    list_sources,
    lookup_feature,
    point_in_feature,
    project_coordinate,
    render_preview_html,
    serialize,
    validate_widget_config,
)


@tool
def map_list_sources() -> str:
    """List supported map source patterns and example sourceIds."""
    return serialize({"sources": list_sources()})


@tool
def map_describe_source(source_id: str, refresh: bool = False) -> str:
    """Describe a real map source and cached geometry summary."""
    try:
        return serialize(describe_source(source_id, refresh=refresh))
    except Exception as error:
        return f"Error: {error}"


@tool
def map_lookup_feature(source_id: str, query: str, refresh: bool = False) -> str:
    """Look up a feature by id or label in a real map source."""
    try:
        return serialize(lookup_feature(source_id, query, refresh=refresh))
    except Exception as error:
        return f"Error: {error}"


@tool
def map_build_widget_config(
    source_id: str,
    interaction_mode: str,
    feature_ids: list[str] | None = None,
    prompt_text: str | None = None,
    compare_source_id: str | None = None,
    timeline_years: list[int] | None = None,
    refresh: bool = False,
) -> str:
    """Build a map widget from a real source-backed boundary provider."""
    try:
        return serialize(
            build_widget_config(
                source_id=source_id,
                interaction_mode=interaction_mode,
                feature_ids=feature_ids,
                prompt_text=prompt_text,
                compare_source_id=compare_source_id,
                timeline_years=timeline_years,
                refresh=refresh,
            )
        )
    except Exception as error:
        return f"Error: {error}"


@tool
def map_validate_widget_config(widget_json: str, refresh: bool = False) -> str:
    """Validate a map widget config against its backing source data."""
    try:
        widget_payload = json.loads(widget_json)
        return serialize(validate_widget_config(widget_payload, refresh=refresh))
    except Exception as error:
        return f"Error: {error}"


@tool
def map_fetch_source(source_id: str, refresh: bool = False) -> str:
    """Fetch and cache source geometry for a sourceId."""
    try:
        bundle = fetch_source_collection(source_id, refresh=refresh)
        return serialize(
            {
                "sourceId": bundle["sourceId"],
                "cachePath": bundle["cachePath"],
                "featureCount": len(bundle["featureCollection"]["features"]),
                "metadata": bundle["metadata"],
            }
        )
    except Exception as error:
        return f"Error: {error}"


@tool
def map_check_point_answer(source_id: str, feature_id: str, lon: float, lat: float, refresh: bool = False) -> str:
    """Check whether a point lies inside a specific source-backed polygon feature."""
    try:
        bundle = fetch_source_collection(source_id, refresh=refresh)
        feature = feature_by_id(bundle["featureCollection"], feature_id)
        return serialize({"sourceId": source_id, "featureId": feature_id, "inside": point_in_feature(feature, lon, lat)})
    except Exception as error:
        return f"Error: {error}"


@tool
def map_check_region_answer(accepted_feature_ids: list[str], learner_feature_ids: list[str], selection_mode: str = "exact") -> str:
    """Evaluate selected feature ids against the expected feature id set."""
    try:
        return serialize(
            evaluate_feature_selection(
                accepted_feature_ids=accepted_feature_ids,
                learner_feature_ids=learner_feature_ids,
                selection_mode=selection_mode,
            )
        )
    except Exception as error:
        return f"Error: {error}"


@tool
def map_check_marker_answer(target_json: str, learner_coordinate_json: str) -> str:
    """Evaluate marker placement against a target coordinate."""
    try:
        target = json.loads(target_json)
        learner_coordinate = json.loads(learner_coordinate_json)
        return serialize(evaluate_marker(learner_coordinate=learner_coordinate, target_coordinate=target))
    except Exception as error:
        return f"Error: {error}"


@tool
def map_check_path_answer(expected_path_json: str, learner_points_json: str) -> str:
    """Evaluate a learner path against an expected path."""
    try:
        expected_path = json.loads(expected_path_json)
        learner_points = json.loads(learner_points_json)
        return serialize(evaluate_path(learner_points=learner_points, expected_path=expected_path))
    except Exception as error:
        return f"Error: {error}"


@tool
def map_check_labels_answer(label_targets_json: str, learner_labels_json: str) -> str:
    """Evaluate learner-supplied labels for source-backed features."""
    try:
        label_targets = json.loads(label_targets_json)
        learner_labels = json.loads(learner_labels_json)
        return serialize(evaluate_labels(learner_labels=learner_labels, label_targets=label_targets))
    except Exception as error:
        return f"Error: {error}"


@tool
def map_generate_guided_artifact(
    source_id: str,
    title: str,
    prompt: str,
    focus_feature_ids: list[str] | None = None,
    compare_source_id: str | None = None,
    refresh: bool = False,
) -> str:
    """Generate a guided map artifact scaffold from a real source-backed map."""
    try:
        return serialize(
            generate_guided_artifact(
                source_id=source_id,
                focus_feature_ids=focus_feature_ids,
                title=title,
                prompt=prompt,
                compare_source_id=compare_source_id,
                refresh=refresh,
            )
        )
    except Exception as error:
        return f"Error: {error}"


@tool
def map_project_coordinates(lon: float, lat: float, from_crs: str = "EPSG:4326", to_crs: str = "EPSG:3857") -> str:
    """Project coordinates into another CRS."""
    try:
        return serialize(project_coordinate(lon, lat, from_crs=from_crs, to_crs=to_crs))
    except Exception as error:
        return f"Error: {error}"


@tool
def map_render_preview(widget_json: str, refresh: bool = False) -> str:
    """Render a temporary HTML preview for a source-backed map widget."""
    try:
        widget_payload = json.loads(widget_json)
        return serialize(render_preview_html(widget_payload, refresh=refresh))
    except Exception as error:
        return f"Error: {error}"


@tool
def map_geocode_place(place_name: str) -> str:
    """Geocode a place name via Nominatim for authoring support."""
    try:
        return serialize(geocode_place(place_name))
    except Exception as error:
        return f"Error: {error}"


GEOGRAPHY_TOOLS: list[BaseTool] = [
    map_list_sources,
    map_describe_source,
    map_fetch_source,
    map_lookup_feature,
    map_build_widget_config,
    map_validate_widget_config,
    map_check_point_answer,
    map_check_region_answer,
    map_check_marker_answer,
    map_check_path_answer,
    map_check_labels_answer,
    map_generate_guided_artifact,
    map_project_coordinates,
    map_render_preview,
    map_geocode_place,
]
