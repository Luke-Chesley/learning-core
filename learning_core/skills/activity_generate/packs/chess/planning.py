from __future__ import annotations

import json
import re

import chess
from langchain_core.messages import HumanMessage, SystemMessage

from learning_core.contracts.activity import ActivityArtifact
from learning_core.contracts.widgets import ChessBoardWidget
from learning_core.runtime.context import RuntimeContext
from learning_core.runtime.providers import ModelRuntime
from learning_core.skills.activity_generate.packs.base import PackPlanningResult
from learning_core.skills.activity_generate.packs.chess.contracts import (
    ChessAcceptedMove,
    ChessBuiltExample,
    ChessBuiltExampleSet,
    ChessExamplePlan,
    ChessExamplePlanSlot,
    ChessValidationReport,
)
from learning_core.skills.activity_generate.scripts.schemas import ActivityGenerationInput
from learning_core.domain.chess_engine import describe_position, normalize_move, validate_fen

_BOARD_CENTERED_PATTERNS = (
    re.compile(r"\bescape check\b", re.IGNORECASE),
    re.compile(r"\bget out of check\b", re.IGNORECASE),
    re.compile(r"\brespond to check\b", re.IGNORECASE),
    re.compile(r"\bmove, block, or capture\b", re.IGNORECASE),
    re.compile(r"\bmove, block, capture\b", re.IGNORECASE),
)

_ESCAPE_CHECK_CATALOG: tuple[dict[str, str], ...] = (
    {
        "conceptTarget": "move",
        "fen": "4k3/8/8/8/8/8/2n5/4K3 w - - 0 1",
        "summary": "The king is checked by a knight, so the escape must come from a king move.",
    },
    {
        "conceptTarget": "move",
        "fen": "4k3/8/8/8/8/8/6n1/4K3 w - - 0 1",
        "summary": "A second king-move escape keeps the recap distinct from the model example.",
    },
    {
        "conceptTarget": "block",
        "fen": "4r1k1/8/8/8/8/3B4/8/4K3 w - - 0 1",
        "summary": "The check travels on a line, so the escape can be taught as a blocking move.",
    },
    {
        "conceptTarget": "capture",
        "fen": "4k3/8/8/8/8/8/3q4/3RK3 w - - 0 1",
        "summary": "Capturing the checking queen is the intended escape idea.",
    },
)


def _extract_json(text: str) -> str:
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def _request_text(payload: ActivityGenerationInput, context: RuntimeContext) -> str:
    lesson = payload.lesson_draft
    parts = [
        payload.subject or "",
        lesson.title,
        lesson.lesson_focus,
        " ".join(payload.linked_skill_titles),
        " ".join(lesson.primary_objectives),
        " ".join(lesson.success_criteria),
        context.user_authored_context.custom_instruction or "",
        " ".join(context.user_authored_context.special_constraints),
    ]
    return " ".join(part.strip() for part in parts if part).strip()


def is_board_centered_chess_lesson(payload: ActivityGenerationInput, context: RuntimeContext) -> bool:
    text = _request_text(payload, context)
    primary_text = " ".join(
        [
            payload.subject or "",
            payload.lesson_draft.title,
            payload.lesson_draft.lesson_focus,
            " ".join(payload.linked_skill_titles),
        ]
    ).lower()
    if not any(
        keyword in primary_text
        for keyword in ("chess", "check", "king", "rook", "bishop", "knight", "queen", "pawn", "fen")
    ):
        return False
    return any(pattern.search(text) for pattern in _BOARD_CENTERED_PATTERNS)


def should_plan_chess_examples(payload: ActivityGenerationInput, context: RuntimeContext) -> bool:
    return is_board_centered_chess_lesson(payload, context)


def _default_escape_check_plan(payload: ActivityGenerationInput) -> ChessExamplePlan:
    lesson_minutes = payload.lesson_draft.total_minutes
    slots = [
        ChessExamplePlanSlot(
            slotId="escape-move",
            taskKind="escape_check",
            conceptTarget="move",
            roleInActivity="model",
            difficulty="intro",
            requiresExplanation=True,
        ),
        ChessExamplePlanSlot(
            slotId="escape-block",
            taskKind="escape_check",
            conceptTarget="block",
            roleInActivity="guided_practice",
            difficulty="core",
            requiresExplanation=True,
        ),
        ChessExamplePlanSlot(
            slotId="escape-capture",
            taskKind="escape_check",
            conceptTarget="capture",
            roleInActivity="check_for_understanding",
            difficulty="core",
            requiresExplanation=False,
        ),
    ]
    if lesson_minutes >= 25:
        slots.append(
            ChessExamplePlanSlot(
                slotId="escape-recap",
                taskKind="escape_check",
                conceptTarget="move",
                roleInActivity="recap",
                difficulty="stretch",
                requiresExplanation=False,
            )
        )
    return ChessExamplePlan(
        lessonFamily="escape_check_responses",
        allowAdditionalBoardExamples=False,
        exampleSlots=slots,
    )


def _planning_prompt(payload: ActivityGenerationInput) -> str:
    lesson = payload.lesson_draft
    return "\n".join(
        [
            "Plan chess teaching slots only. Do not write an ActivityArtifact.",
            "Return one JSON object with shape:",
            '{"lessonFamily":"escape_check_responses","allowAdditionalBoardExamples":false,"exampleSlots":[{"slotId":"...","taskKind":"escape_check","conceptTarget":"move|block|capture","roleInActivity":"model|guided_practice|check_for_understanding|recap","difficulty":"intro|core|stretch","requiresExplanation":true,"acceptanceMode":"engine_derived_escape_set"}]}',
            "",
            "Rules:",
            "- Plan pedagogical slots, not FENs.",
            "- Cover move, block, and capture distinctly before any recap slot.",
            "- Keep the plan small and concrete.",
            f"- Session budget is {lesson.total_minutes} minutes. Use 3 core slots for sessions under 25 minutes. Add a recap slot only for 25+ minute sessions.",
            "",
            f"Session budget: {lesson.total_minutes} minutes",
            f"Lesson title: {lesson.title}",
            f"Lesson focus: {lesson.lesson_focus}",
            f"Objectives: {'; '.join(lesson.primary_objectives)}",
            f"Success criteria: {'; '.join(lesson.success_criteria)}",
            f"Linked skills: {', '.join(payload.linked_skill_titles)}",
        ]
    )


def plan_chess_examples(
    payload: ActivityGenerationInput,
    context: RuntimeContext,
    model_runtime: ModelRuntime,
) -> ChessExamplePlan:
    del context
    try:
        response = model_runtime.client.invoke(
            [
                SystemMessage(content="Plan a compact chess example set as strict JSON."),
                HumanMessage(content=_planning_prompt(payload)),
            ]
        )
        content = getattr(response, "content", "")
        if isinstance(content, list):
            content = "".join(
                item.get("text", "") if isinstance(item, dict) else str(item)
                for item in content
            )
        return ChessExamplePlan.model_validate(json.loads(_extract_json(str(content))))
    except Exception:
        return _default_escape_check_plan(payload)


def _board(fen: str) -> chess.Board:
    return chess.Board(validate_fen(fen))


def _move_category(board: chess.Board, move: chess.Move) -> str | None:
    candidate = board.copy(stack=False)
    candidate.push(move)
    if candidate.is_check():
        return None

    checkers = set(chess.SquareSet(board.checkers()))
    if not checkers:
        return None

    piece = board.piece_at(move.from_square)
    if piece is None:
        return None

    if board.is_capture(move) and move.to_square in checkers:
        return "capture"
    if piece.piece_type == chess.KING:
        return "move"

    if len(checkers) != 1:
        return None
    checker_square = next(iter(checkers))
    checking_piece = board.piece_at(checker_square)
    king_square = board.king(board.turn)
    if checking_piece is None or king_square is None:
        return None
    if checking_piece.piece_type not in (chess.BISHOP, chess.ROOK, chess.QUEEN):
        return None
    between_squares = set(chess.SquareSet(chess.between(king_square, checker_square)))
    if move.to_square in between_squares:
        return "block"
    return None


def _accepted_escape_moves(fen: str, concept_target: str) -> list[ChessAcceptedMove]:
    board = _board(fen)
    if not board.is_check():
        raise ValueError("Escape-check examples require an in-check position.")

    accepted: list[ChessAcceptedMove] = []
    for move in board.legal_moves:
        if _move_category(board, move) != concept_target:
            continue
        normalized = normalize_move(board.fen(), move.uci())
        accepted.append(
            ChessAcceptedMove(
                uci=normalized["uci"],
                san=normalized["san"],
                fromSquare=normalized["from"],
                toSquare=normalized["to"],
                moveCategory=concept_target,
            )
        )
    if not accepted:
        raise ValueError(f"No accepted {concept_target} moves were found for {fen}.")
    return accepted


def _widget_config(fen: str, accepted_moves: list[ChessAcceptedMove], concept_target: str) -> dict:
    widget = ChessBoardWidget(
        surfaceKind="board_surface",
        engineKind="chess",
        state={"fen": fen},
        display={
            "showSideToMove": True,
            "showCoordinates": True,
            "showMoveHint": True,
            "boardRole": "primary",
        },
        interaction={
            "mode": "move_input",
            "submissionMode": "immediate",
            "selectionMode": "click_click",
            "showLegalTargets": True,
            "allowReset": True,
            "resetPolicy": "reset_to_initial",
            "attemptPolicy": "allow_retry",
        },
        feedback={"mode": "immediate", "displayMode": "inline"},
        evaluation={"expectedMoves": [move.uci for move in accepted_moves]},
        annotations={
            "highlightSquares": sorted({move.fromSquare for move in accepted_moves}),
            "arrows": [],
        },
        instructionText=f"Escape the check by using a {concept_target} response.",
        caption="Validated by the chess engine before final composition.",
    )
    return widget.model_dump(mode="json", exclude_none=True)


def _component_id(slot: ChessExamplePlanSlot) -> str:
    return f"chess-{slot.roleInActivity}-{slot.conceptTarget}-{slot.slotId}"


def build_chess_example_set(plan: ChessExamplePlan) -> ChessBuiltExampleSet:
    used_fens: set[str] = set()
    built_examples: list[ChessBuiltExample] = []

    for slot in plan.exampleSlots:
        if slot.taskKind != "escape_check":
            raise ValueError(f"Unsupported taskKind for chess planning: {slot.taskKind}")

        chosen_entry: dict[str, str] | None = None
        for entry in _ESCAPE_CHECK_CATALOG:
            if entry["conceptTarget"] != slot.conceptTarget:
                continue
            normalized_fen = validate_fen(entry["fen"])
            if normalized_fen in used_fens:
                continue
            chosen_entry = {**entry, "fen": normalized_fen}
            break
        if chosen_entry is None:
            raise ValueError(f"No distinct chess catalog example is available for concept '{slot.conceptTarget}'.")

        accepted_moves = _accepted_escape_moves(chosen_entry["fen"], slot.conceptTarget)
        position = describe_position(chosen_entry["fen"])
        widget = _widget_config(chosen_entry["fen"], accepted_moves, slot.conceptTarget)
        built_examples.append(
            ChessBuiltExample(
                slotId=slot.slotId,
                componentId=_component_id(slot),
                taskKind=slot.taskKind,
                conceptTarget=slot.conceptTarget,
                roleInActivity=slot.roleInActivity,
                acceptanceMode=slot.acceptanceMode,
                difficulty=slot.difficulty,
                requiresExplanation=slot.requiresExplanation,
                fen=chosen_entry["fen"],
                sideToMove=position["sideToMove"],
                isCheck=position["isCheck"],
                acceptedMoves=accepted_moves,
                engineSummary=chosen_entry["summary"],
                widget=widget,
            )
        )
        used_fens.add(chosen_entry["fen"])

    example_set = ChessBuiltExampleSet(
        lessonFamily=plan.lessonFamily,
        examples=built_examples,
    )
    report = validate_chess_example_set(example_set)
    if not report.valid:
        raise ValueError("; ".join(report.hardErrors))
    return example_set


def validate_chess_example_set(example_set: ChessBuiltExampleSet) -> ChessValidationReport:
    hard_errors: list[str] = []
    soft_warnings: list[str] = []
    duplicate_fens: list[str] = []

    fens = [example.fen for example in example_set.examples]
    seen_fens: set[str] = set()
    for fen in fens:
        if fen in seen_fens and fen not in duplicate_fens:
            duplicate_fens.append(fen)
        seen_fens.add(fen)
    if duplicate_fens:
        hard_errors.append("Validated chess example set contains duplicate FENs.")

    coverage_targets = [
        example.conceptTarget
        for example in example_set.examples
        if example.roleInActivity != "recap"
    ]
    if {"move", "block", "capture"} - set(coverage_targets):
        hard_errors.append("Validated chess example set must cover move, block, and capture before recap.")

    if len(coverage_targets) != len(set(coverage_targets)):
        hard_errors.append("Core chess slots must not duplicate concept targets.")

    for example in example_set.examples:
        if not example.isCheck:
            hard_errors.append(f"Example '{example.slotId}' is not actually an in-check position.")
        if example.widget["evaluation"]["expectedMoves"] != [move.uci for move in example.acceptedMoves]:
            hard_errors.append(f"Example '{example.slotId}' drifted from engine-derived expected moves.")

    return ChessValidationReport(
        valid=not hard_errors,
        hardErrors=hard_errors,
        softWarnings=soft_warnings,
        coverageTargets=sorted(set(coverage_targets)),
        duplicateFens=duplicate_fens,
    )


def validate_chess_artifact_against_example_set(
    artifact: ActivityArtifact,
    example_set: ChessBuiltExampleSet,
) -> ChessValidationReport:
    hard_errors: list[str] = []
    soft_warnings: list[str] = []
    matched_slots: list[str] = []
    missing_slots: list[str] = []

    actual_components = {
        component.id: component
        for component in artifact.components
        if component.type == "interactive_widget" and component.widget.engineKind == "chess"
    }
    expected_ids = {example.componentId for example in example_set.examples}

    for example in example_set.examples:
        component = actual_components.get(example.componentId)
        if component is None:
            missing_slots.append(example.slotId)
            hard_errors.append(f'Validated chess example "{example.componentId}" is missing from the final activity.')
            continue

        widget = component.widget.model_dump(mode="json", exclude_none=True)
        if widget["state"]["fen"] != example.widget["state"]["fen"]:
            hard_errors.append(f'Interactive widget "{component.id}" changed FEN after validation.')
        if widget["state"]["initialFen"] != example.widget["state"]["initialFen"]:
            hard_errors.append(f'Interactive widget "{component.id}" changed initialFen after validation.')
        if widget["interaction"]["mode"] != example.widget["interaction"]["mode"]:
            hard_errors.append(f'Interactive widget "{component.id}" changed interaction.mode after validation.')
        if widget["evaluation"]["expectedMoves"] != example.widget["evaluation"]["expectedMoves"]:
            hard_errors.append(f'Interactive widget "{component.id}" changed expectedMoves after validation.')
        matched_slots.append(example.slotId)

    extra_widget_ids = sorted(set(actual_components) - expected_ids)
    if extra_widget_ids:
        hard_errors.append(
            "Final activity introduced extra chess widgets outside the validated example set: "
            + ", ".join(extra_widget_ids)
        )

    return ChessValidationReport(
        valid=not hard_errors,
        hardErrors=hard_errors,
        softWarnings=soft_warnings,
        matchedSlots=matched_slots,
        missingSlots=missing_slots,
    )


def render_chess_example_summary(example_set: ChessBuiltExampleSet) -> str:
    component_templates = [
        {
            "componentId": example.componentId,
            "slotId": example.slotId,
            "roleInActivity": example.roleInActivity,
            "conceptTarget": example.conceptTarget,
            "engineSummary": example.engineSummary,
            "widget": example.widget,
        }
        for example in example_set.examples
    ]
    return "\n".join(
        [
            "Use the following validated chess examples as fixed board-position inputs for final composition.",
            "Preserve `componentId`, `widget.state`, `widget.interaction`, and `widget.evaluation.expectedMoves`.",
            "You may adapt only the learner-facing prompt, instructionText, and caption around these validated widgets.",
            "",
            "```json",
            json.dumps(component_templates, indent=2),
            "```",
        ]
    )


def run_chess_planning_phase(
    payload: ActivityGenerationInput,
    context: RuntimeContext,
    model_runtime: ModelRuntime,
) -> PackPlanningResult | None:
    if not should_plan_chess_examples(payload, context):
        return None

    plan = plan_chess_examples(payload, context, model_runtime)
    example_set = build_chess_example_set(plan)
    return PackPlanningResult(
        pack_name="chess",
        prompt_sections=(render_chess_example_summary(example_set),),
        structured_data={
            "phase": "chess_example_planning",
            "plan": plan.model_dump(mode="json", exclude_none=True),
            "validated_examples": example_set.model_dump(mode="json", exclude_none=True),
        },
    )
