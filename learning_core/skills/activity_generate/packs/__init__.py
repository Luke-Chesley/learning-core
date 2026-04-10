from learning_core.skills.activity_generate.packs.base import Pack
from learning_core.skills.activity_generate.packs.chess.pack import ChessPack
from learning_core.skills.activity_generate.packs.math.pack import MathPack

ALL_PACKS: tuple[Pack, ...] = (ChessPack(), MathPack())

__all__ = ["ALL_PACKS", "Pack"]
