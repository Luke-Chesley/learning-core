from __future__ import annotations

from pathlib import Path

from langchain_core.tools import BaseTool

from learning_core.contracts.activity import ActivityArtifact
from learning_core.runtime.context import RuntimeContext
from learning_core.runtime.providers import ModelRuntime
from learning_core.skills.activity_generate.packs.base import PackPlanningResult, PackValidator
from learning_core.skills.activity_generate.packs.math.tools import MATH_TOOLS
from learning_core.skills.activity_generate.scripts.schemas import ActivityGenerationInput

_PACK_DIR = Path(__file__).resolve().parent
_DOC_FILENAMES = ("pack.md", "patterns.md", "examples.md")

_KEYWORDS: tuple[str, ...] = (
    "math",
    "arithmetic",
    "fraction",
    "fractions",
    "division",
    "long division",
    "multiply",
    "multiplication",
    "addition",
    "subtraction",
    "algebra",
    "equation",
    "geometry",
    "decimal",
    "decimals",
    "percent",
    "ratio",
    "measurement",
    "word problem",
    "place value",
    "number line",
)


class MathPack:
    @property
    def name(self) -> str:
        return "math"

    @property
    def keywords(self) -> tuple[str, ...]:
        return _KEYWORDS

    def prompt_sections(self) -> list[str]:
        sections: list[str] = []
        for filename in _DOC_FILENAMES:
            sections.append((_PACK_DIR / filename).read_text(encoding="utf-8").strip())
        return sections

    def needs_planning(self, payload: ActivityGenerationInput, context: RuntimeContext) -> bool:
        return False

    def run_planning_phase(
        self,
        payload: ActivityGenerationInput,
        context: RuntimeContext,
        model_runtime: ModelRuntime,
    ) -> PackPlanningResult | None:
        return None

    def tools(self) -> list[BaseTool]:
        return list(MATH_TOOLS)

    def auto_injected_ui_specs(self) -> list[str]:
        return []

    def validators(self) -> list[PackValidator]:
        return []

    def required_tool_names(self) -> list[str]:
        return []

    def repair_guidance(self) -> str | None:
        return None

    def detect_pack_widgets(self, artifact: ActivityArtifact) -> list[str]:
        return []
