from __future__ import annotations

import json
from pathlib import Path

from langchain_core.tools import tool

from learning_core.domain.chess_engine import apply_move, describe_position, legal_moves, normalize_move

_SKILL_DIR = Path(__file__).resolve().parent.parent

ALLOWED_UI_SPEC_PATHS: frozenset[str] = frozenset(
    {
        "ui_components/heading.md",
        "ui_components/paragraph.md",
        "ui_components/callout.md",
        "ui_components/image.md",
        "ui_components/divider.md",
        "ui_components/short_answer.md",
        "ui_components/text_response.md",
        "ui_components/rich_text_response.md",
        "ui_components/single_select.md",
        "ui_components/multi_select.md",
        "ui_components/rating.md",
        "ui_components/confidence_check.md",
        "ui_components/checklist.md",
        "ui_components/ordered_sequence.md",
        "ui_components/matching_pairs.md",
        "ui_components/categorization.md",
        "ui_components/sort_into_groups.md",
        "ui_components/label_map.md",
        "ui_components/hotspot_select.md",
        "ui_components/build_steps.md",
        "ui_components/drag_arrange.md",
        "ui_components/interactive_widget.md",
        "ui_components/reflection_prompt.md",
        "ui_components/rubric_self_check.md",
        "ui_components/file_upload.md",
        "ui_components/image_capture.md",
        "ui_components/audio_capture.md",
        "ui_components/observation_record.md",
        "ui_components/teacher_checkoff.md",
        "ui_components/compare_and_explain.md",
        "ui_components/choose_next_step.md",
        "ui_components/construction_space.md",
        "ui_widgets/board_surface__chess.md",
        "ui_widgets/expression_surface__math_symbolic.md",
        "ui_widgets/graph_surface__graphing.md",
    }
)

ACTIVITY_GENERATE_ALLOWED_TOOLS: tuple[str, ...] = (
    "read_ui_spec",
    "chess_legal_moves",
    "chess_describe_position",
    "chess_apply_move",
    "chess_normalize_move",
)


def _serialize_tool_payload(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True)


def _resolve_ui_spec_path(path: str) -> Path:
    normalized = path.strip().replace("\\", "/")
    if normalized.startswith("./"):
        normalized = normalized[2:]

    parts = [part for part in normalized.split("/") if part]
    if not parts or any(part == ".." for part in parts):
        raise ValueError(
            f"invalid path '{path}'. Use exact allowlisted paths from the registry index, such as "
            "'ui_components/short_answer.md' or 'ui_widgets/board_surface__chess.md'."
        )

    candidate = "/".join(parts)
    if candidate not in ALLOWED_UI_SPEC_PATHS and len(parts) == 1:
        matches = [allowed_path for allowed_path in ALLOWED_UI_SPEC_PATHS if allowed_path.endswith(f"/{parts[0]}")]
        if len(matches) == 1:
            candidate = matches[0]

    if candidate not in ALLOWED_UI_SPEC_PATHS:
        raise ValueError(f"'{path}' is not a recognized UI spec. Check the registry index for valid paths.")

    return _SKILL_DIR / candidate


@tool
def read_ui_spec(path: str) -> str:
    """Read the full documentation for an allowlisted UI component or widget spec.

    Pass the exact path from the registry index, such as 'ui_components/short_answer.md'
    or 'ui_widgets/board_surface__chess.md'.
    """
    try:
        spec_path = _resolve_ui_spec_path(path)
        return spec_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return f"Error: UI spec not found at {path}"
    except ValueError as error:
        return f"Error: {error}"


@tool
def chess_legal_moves(fen: str) -> str:
    """Return normalized legal chess moves for a FEN position."""
    try:
        return _serialize_tool_payload({"legalMoves": legal_moves(fen)})
    except ValueError as error:
        return f"Error: {error}"


@tool
def chess_describe_position(fen: str) -> str:
    """Return a compact chess position summary for a FEN position."""
    try:
        return _serialize_tool_payload(describe_position(fen))
    except ValueError as error:
        return f"Error: {error}"


@tool
def chess_apply_move(fen: str, move: str) -> str:
    """Apply a legal move to a FEN position and return the resulting state."""
    try:
        return _serialize_tool_payload(apply_move(fen, move))
    except ValueError as error:
        return f"Error: {error}"


@tool
def chess_normalize_move(fen: str, move: str) -> str:
    """Normalize a SAN or UCI move against a FEN position."""
    try:
        return _serialize_tool_payload(normalize_move(fen, move))
    except ValueError as error:
        return f"Error: {error}"
