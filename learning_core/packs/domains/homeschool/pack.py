from __future__ import annotations

from pathlib import Path

from learning_core.packs.base import RuntimePackDefinition

_PACK_DIR = Path(__file__).resolve().parent


def build_homeschool_pack() -> RuntimePackDefinition:
    return RuntimePackDefinition(
        name="homeschool",
        category="domain",
        prompt_sections=((_PACK_DIR / "prompt.md").read_text(encoding="utf-8").strip(),),
        metadata={"source": "template"},
    )
