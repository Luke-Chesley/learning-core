from __future__ import annotations

from pathlib import Path

from langchain_core.tools import tool

_UI_COMPONENTS_DIR = Path(__file__).resolve().parent.parent / "ui_components"

ALLOWED_COMPONENT_DOCS: frozenset[str] = frozenset(
    {
        "heading.md",
        "paragraph.md",
        "callout.md",
        "image.md",
        "divider.md",
        "short_answer.md",
        "text_response.md",
        "rich_text_response.md",
        "single_select.md",
        "multi_select.md",
        "rating.md",
        "confidence_check.md",
        "checklist.md",
        "ordered_sequence.md",
        "matching_pairs.md",
        "categorization.md",
        "sort_into_groups.md",
        "label_map.md",
        "hotspot_select.md",
        "build_steps.md",
        "drag_arrange.md",
        "reflection_prompt.md",
        "rubric_self_check.md",
        "file_upload.md",
        "image_capture.md",
        "audio_capture.md",
        "observation_record.md",
        "teacher_checkoff.md",
        "compare_and_explain.md",
        "choose_next_step.md",
        "construction_space.md",
    }
)

ACTIVITY_GENERATE_ALLOWED_TOOLS: tuple[str, ...] = ("read_ui_component",)


@tool
def read_ui_component(path: str) -> str:
    """Read the full documentation for a UI component type.

    Pass the doc path from the registry index, e.g. 'ui_components/short_answer.md'.
    Returns the complete component doc including fields, examples, and usage guidance.
    """
    filename = path.removeprefix("ui_components/")

    if ".." in filename or "/" in filename:
        return f"Error: invalid path '{path}'. Use exact paths from the registry index (e.g. 'ui_components/short_answer.md')."

    if filename not in ALLOWED_COMPONENT_DOCS:
        return f"Error: '{path}' is not a recognized component doc. Check the registry index for valid paths."

    doc_path = _UI_COMPONENTS_DIR / filename
    try:
        return doc_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return f"Error: component doc not found at {doc_path}"
