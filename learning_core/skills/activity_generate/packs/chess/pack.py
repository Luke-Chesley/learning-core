from __future__ import annotations

from pathlib import Path

from langchain_core.tools import BaseTool

from learning_core.skills.activity_generate.packs.chess.tools import CHESS_TOOLS

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
