from __future__ import annotations

import json
from typing import Any, Optional

from langchain_core.tools import BaseTool, tool


def _serialize(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True)


@tool
def math_validate_widget_config(
    engine_kind: str,
    interaction_mode: str,
    expected_expression: Optional[str] = None,
    expected_graph_description: Optional[str] = None,
    prompt_latex: Optional[str] = None,
    equivalence_mode: Optional[str] = None,
    surface_role: Optional[str] = None,
    prompt_text: Optional[str] = None,
) -> str:
    """Validate a math widget configuration for structural coherence.

    Checks that the combination of interaction mode, evaluation fields,
    and display settings is internally consistent. Works for both
    math_symbolic and graphing engine kinds.
    """
    result: dict[str, Any] = {"valid": True, "errors": [], "warnings": []}
    result["engineKind"] = engine_kind
    result["interactionMode"] = interaction_mode

    if engine_kind not in ("math_symbolic", "graphing"):
        result["valid"] = False
        result["errors"].append(f"Unknown engine kind: {engine_kind}")
        return _serialize(result)

    if engine_kind == "math_symbolic":
        valid_modes = ("view_only", "expression_entry", "equation_entry", "step_entry")
        if interaction_mode not in valid_modes:
            result["valid"] = False
            result["errors"].append(f"Invalid interaction mode '{interaction_mode}' for math_symbolic. Must be one of: {', '.join(valid_modes)}")
            return _serialize(result)

        has_expected = expected_expression is not None and expected_expression.strip() != ""

        if interaction_mode != "view_only" and not has_expected:
            result["valid"] = False
            result["errors"].append("Input mode requires evaluation.expectedExpression.")

        if interaction_mode == "view_only" and has_expected:
            result["valid"] = False
            result["errors"].append("view_only mode should not include evaluation.expectedExpression.")

        if interaction_mode != "view_only" and not prompt_latex:
            result["valid"] = False
            result["errors"].append("Input mode requires state.promptLatex to frame the problem.")

        if equivalence_mode and equivalence_mode not in ("exact", "simplified", "equivalent"):
            result["warnings"].append(f"Unrecognized equivalenceMode '{equivalence_mode}'. Expected: exact, simplified, or equivalent.")

    elif engine_kind == "graphing":
        valid_modes = ("view_only", "plot_point", "plot_curve", "analyze_graph")
        if interaction_mode not in valid_modes:
            result["valid"] = False
            result["errors"].append(f"Invalid interaction mode '{interaction_mode}' for graphing. Must be one of: {', '.join(valid_modes)}")
            return _serialize(result)

        has_expected = expected_graph_description is not None and expected_graph_description.strip() != ""

        if interaction_mode != "view_only" and not has_expected:
            result["valid"] = False
            result["errors"].append("Input mode requires evaluation.expectedGraphDescription.")

        if interaction_mode == "view_only" and has_expected:
            result["valid"] = False
            result["errors"].append("view_only mode should not include evaluation.expectedGraphDescription.")

    if surface_role and surface_role != "primary" and interaction_mode != "view_only":
        result["warnings"].append("Input widgets should generally use surfaceRole 'primary'.")

    return _serialize(result)


MATH_TOOLS: list[BaseTool] = [
    math_validate_widget_config,
]
