from __future__ import annotations

from pathlib import Path

from langchain_core.tools import BaseTool

from learning_core.contracts.activity import ActivityArtifact
from learning_core.skills.activity_generate.packs.base import PackValidator
from learning_core.skills.activity_generate.packs.chess.tools import CHESS_TOOLS
from learning_core.skills.activity_generate.packs.chess.validation import ChessValidator

_PACK_DIR = Path(__file__).resolve().parent
_DOC_FILENAMES = ("pack.md", "patterns.md", "examples.md")

_KEYWORDS: tuple[str, ...] = (
    "chess",
    "checkmate",
    "check",
    "opening",
    "middlegame",
    "endgame",
    "fork",
    "pin",
    "skewer",
    "tactic",
    "tactics",
    "candidate move",
    "best move",
    "threat",
    "blunder",
    "zugzwang",
    "mate",
    "rook",
    "bishop",
    "knight",
    "queen",
    "king",
    "pawn",
    "fen",
)

_AUTO_INJECTED_UI_SPECS: list[str] = [
    "ui_components/interactive_widget.md",
    "ui_widgets/board_surface__chess.md",
]

_REQUIRED_TOOL_NAMES: list[str] = [
    "chess_validate_widget_config",
    "chess_legal_moves",
    "chess_describe_position",
    "chess_apply_move",
    "chess_normalize_move",
]

_REPAIR_GUIDANCE = (
    "The activity contains chess board widgets but no chess validation tools were used during generation. "
    "Before finalizing, validate each chess widget using the chess_validate_widget_config tool. "
    "Pass the widget's FEN, expectedMoves, highlightSquares, arrows, and any prompt text that makes claims about the position. "
    "Fix any issues the tool reports before returning the corrected JSON."
)


class ChessPack:
    @property
    def name(self) -> str:
        return "chess"

    @property
    def keywords(self) -> tuple[str, ...]:
        return _KEYWORDS

    def prompt_sections(self) -> list[str]:
        sections: list[str] = []
        for filename in _DOC_FILENAMES:
            sections.append((_PACK_DIR / filename).read_text(encoding="utf-8").strip())
        return sections

    def tools(self) -> list[BaseTool]:
        return list(CHESS_TOOLS)

    def auto_injected_ui_specs(self) -> list[str]:
        return list(_AUTO_INJECTED_UI_SPECS)

    def validators(self) -> list[PackValidator]:
        return [ChessValidator()]

    def required_tool_names(self) -> list[str]:
        return list(_REQUIRED_TOOL_NAMES)

    def repair_guidance(self) -> str | None:
        return _REPAIR_GUIDANCE

    def detect_pack_widgets(self, artifact: ActivityArtifact) -> list[str]:
        return [
            component.id
            for component in artifact.components
            if component.type == "interactive_widget" and component.widget.engineKind == "chess"
        ]
