from __future__ import annotations

from pathlib import Path

from langchain_core.tools import BaseTool

from learning_core.contracts.activity import ActivityArtifact
from learning_core.runtime.context import RuntimeContext
from learning_core.runtime.providers import ModelRuntime
from learning_core.skills.activity_generate.packs.base import PackPlanningResult, PackValidator
from learning_core.skills.activity_generate.packs.math.tools import MATH_TOOLS
from learning_core.skills.activity_generate.packs.math.validation import MathValidator
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

_AUTO_INJECTED_UI_SPECS: list[str] = [
    "ui_components/interactive_widget.md",
    "ui_widgets/expression_surface__math_symbolic.md",
    "ui_widgets/graph_surface__graphing.md",
]

_REQUIRED_TOOL_NAMES: list[str] = [
    "math_validate_widget_config",
]

_REPAIR_GUIDANCE = (
    "The activity contains math widgets but no math validation tools were used during generation. "
    "Before finalizing, validate each math widget using the math_validate_widget_config tool. "
    "For expression_entry widgets, ensure state.promptLatex and evaluation.expectedExpression are set. "
    "For graphing widgets, ensure evaluation.expectedGraphDescription is set."
)


class MathPack:
    @property
    def name(self) -> str:
        return "math"

    @property
    def keywords(self) -> tuple[str, ...]:
        return _KEYWORDS

    def prompt_sections(self) -> list[str]:
        return [(_PACK_DIR / filename).read_text(encoding="utf-8").strip() for filename in _DOC_FILENAMES]

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
        return list(_AUTO_INJECTED_UI_SPECS)

    def validators(self) -> list[PackValidator]:
        return [MathValidator()]

    def required_tool_names(self) -> list[str]:
        return list(_REQUIRED_TOOL_NAMES)

    def repair_guidance(self) -> str | None:
        return _REPAIR_GUIDANCE

    def detect_pack_widgets(self, artifact: ActivityArtifact) -> list[str]:
        return [
            component.id
            for component in artifact.components
            if component.type == "interactive_widget"
            and component.widget.engineKind in ("math_symbolic", "graphing")
        ]
