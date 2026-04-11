from __future__ import annotations

from pathlib import Path

from langchain_core.tools import BaseTool

from learning_core.contracts.activity import ActivityArtifact
from learning_core.runtime.context import RuntimeContext
from learning_core.runtime.providers import ModelRuntime
from learning_core.skills.activity_generate.packs.base import PackPlanningResult, PackValidator
from learning_core.skills.activity_generate.packs.chess.planning import (
    run_chess_planning_phase,
    should_plan_chess_examples,
)
from learning_core.skills.activity_generate.packs.chess.tools import CHESS_PLANNING_TOOLS, CHESS_TOOLS
from learning_core.skills.activity_generate.packs.chess.validation import ChessValidator
from learning_core.skills.activity_generate.scripts.schemas import ActivityGenerationInput

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
    "chess_build_example_set",
    "chess_validate_example_set",
    "chess_validate_widget_config",
    "chess_legal_moves",
    "chess_describe_position",
    "chess_apply_move",
    "chess_normalize_move",
]

_REPAIR_GUIDANCE = (
    "The activity contains chess board widgets but no chess validation tools were used during generation. "
    "Before finalizing, validate each chess widget using the chess_validate_widget_config tool. "
    "For board-centered lessons, prefer the engine-backed chess_build_example_set flow and reuse those validated examples in the final artifact."
)


class ChessPack:
    @property
    def name(self) -> str:
        return "chess"

    @property
    def keywords(self) -> tuple[str, ...]:
        return _KEYWORDS

    def prompt_sections(self) -> list[str]:
        return [(_PACK_DIR / filename).read_text(encoding="utf-8").strip() for filename in _DOC_FILENAMES]

    def needs_planning(self, payload: ActivityGenerationInput, context: RuntimeContext) -> bool:
        return should_plan_chess_examples(payload, context)

    def run_planning_phase(
        self,
        payload: ActivityGenerationInput,
        context: RuntimeContext,
        model_runtime: ModelRuntime,
    ) -> PackPlanningResult | None:
        return run_chess_planning_phase(payload, context, model_runtime)

    def tools(self) -> list[BaseTool]:
        return [*CHESS_TOOLS, *CHESS_PLANNING_TOOLS]

    def planning_tools(self) -> list[BaseTool]:
        return list(CHESS_PLANNING_TOOLS)

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
