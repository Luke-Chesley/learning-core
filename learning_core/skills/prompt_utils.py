from __future__ import annotations

from typing import Iterable

from learning_core.contracts.curriculum import CurriculumChatMessage
from learning_core.runtime.context import RuntimeContext


def format_curriculum_transcript(messages: Iterable[CurriculumChatMessage]) -> str:
    rows = [
        f"{index + 1}. {'Assistant' if message.role == 'assistant' else 'Parent'}: {message.content}"
        for index, message in enumerate(messages)
    ]
    return "\n".join(rows) if rows else "No conversation yet."


def append_user_authored_context(lines: list[str], context: RuntimeContext) -> None:
    authored = context.user_authored_context

    if authored.parent_goal:
        lines.extend(["", f"Parent goal: {authored.parent_goal}"])

    if authored.note:
        lines.extend(["", f"Note: {authored.note}"])

    if authored.teacher_note:
        lines.extend(["", f"Teacher note: {authored.teacher_note}"])

    if authored.special_constraints:
        lines.append("")
        lines.append("Special constraints:")
        for value in authored.special_constraints:
            lines.append(f"- {value}")

    if authored.avoidances:
        lines.append("")
        lines.append("Avoid:")
        for value in authored.avoidances:
            lines.append(f"- {value}")

    if authored.custom_instruction:
        lines.extend(["", f"Custom instruction: {authored.custom_instruction}"])
