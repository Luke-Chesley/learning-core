from __future__ import annotations

from pathlib import Path
from typing import Iterable

from learning_core.contracts.curriculum import CurriculumChatMessage
from learning_core.runtime.context import RuntimeContext


def format_curriculum_transcript(messages: Iterable[CurriculumChatMessage]) -> str:
    rows = [
        f"{index + 1}. {'Assistant' if message.role == 'assistant' else 'Parent'}: {message.content}"
        for index, message in enumerate(messages)
    ]
    return "\n".join(rows) if rows else "No conversation yet."


def format_source_files(source_files: Iterable[object]) -> str:
    rows: list[str] = []
    for index, source_file in enumerate(source_files, start=1):
        file_name = getattr(source_file, "fileName", "file")
        mime_type = getattr(source_file, "mimeType", "application/octet-stream")
        modality = getattr(source_file, "modality", "file")
        title = getattr(source_file, "title", "Untitled source")
        rows.append(f"{index}. {title} ({modality}) -> {file_name} [{mime_type}]")
    return "\n".join(rows) if rows else "No attached source files."


def _is_image_source_file(source_file: object) -> bool:
    modality = str(getattr(source_file, "modality", "") or "").lower()
    if modality in {"image", "photo"}:
        return True

    mime_type = str(getattr(source_file, "mimeType", "") or "").lower()
    if mime_type.startswith("image/"):
        return True

    extension = Path(str(getattr(source_file, "fileName", "") or "")).suffix.lower()
    return extension in {
        ".avif",
        ".bmp",
        ".gif",
        ".heic",
        ".heif",
        ".jpeg",
        ".jpg",
        ".png",
        ".svg",
        ".tif",
        ".tiff",
        ".webp",
    }


def build_openai_file_blocks(source_files: Iterable[object]) -> list[dict[str, object]]:
    blocks: list[dict[str, object]] = []
    for source_file in source_files:
        file_data = getattr(source_file, "fileData", None)
        is_image = _is_image_source_file(source_file)
        if file_data:
            if is_image:
                blocks.append(
                    {
                        "type": "input_image",
                        "image_url": file_data,
                    }
                )
            else:
                blocks.append(
                    {
                        "type": "input_file",
                        "filename": getattr(source_file, "fileName", "file"),
                        "file_data": file_data,
                    }
                )
            continue

        file_url = getattr(source_file, "fileUrl", None)
        if file_url:
            if is_image:
                blocks.append(
                    {
                        "type": "input_image",
                        "image_url": file_url,
                    }
                )
            else:
                blocks.append(
                    {
                        "type": "input_file",
                        "file_url": file_url,
                    }
                )
            continue

        raise ValueError("Expected source file to include fileUrl or fileData.")
    return blocks


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
