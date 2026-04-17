from __future__ import annotations

from learning_core.contracts.curriculum import CurriculumGenerationRequest
from learning_core.contracts.operation import AppContext, PresentationContext, UserAuthoredContext
from learning_core.runtime.context import RuntimeContext
from learning_core.skills.curriculum_generate.scripts.main import CurriculumGenerateSkill


def _payload() -> CurriculumGenerationRequest:
    return CurriculumGenerationRequest.model_validate(
        {
            "learnerName": "Maya",
            "messages": [
                {
                    "role": "user",
                    "content": "Build a homeschool curriculum from this source.",
                }
            ],
            "sourcePackages": [
                {
                    "id": "ipkg-1",
                    "title": "Ancient Egypt reader",
                    "modality": "pdf",
                    "summary": "PDF reader about ancient Egypt",
                    "extractionStatus": "ready",
                    "assetCount": 1,
                    "assetIds": ["asset-1"],
                    "detectedChunks": ["Uploaded PDF: egypt-reader.pdf"],
                    "sourceFingerprint": "fp-1",
                }
            ],
            "sourceFiles": [
                {
                    "assetId": "asset-1",
                    "packageId": "ipkg-1",
                    "title": "Ancient Egypt reader",
                    "modality": "pdf",
                    "fileName": "egypt-reader.pdf",
                    "mimeType": "application/pdf",
                    "fileUrl": "https://example.com/egypt-reader.pdf",
                }
            ],
        }
    )


def _context() -> RuntimeContext:
    return RuntimeContext.create(
        operation_name="curriculum_generate",
        app_context=AppContext(product="homeschool-v2", surface="curriculum"),
        presentation_context=PresentationContext(),
        user_authored_context=UserAuthoredContext(),
    )


def test_curriculum_generate_prompt_preview_mentions_attached_source_files():
    preview = CurriculumGenerateSkill().build_prompt_preview(_payload(), _context())

    assert "Source packages:" in preview.user_prompt
    assert "Ancient Egypt reader" in preview.user_prompt
    assert "Attached source files:" in preview.user_prompt
    assert "egypt-reader.pdf" in preview.user_prompt


def test_curriculum_generate_builds_openai_file_message_blocks():
    content = CurriculumGenerateSkill().build_user_message_content(
        _payload(),
        _context(),
        provider="openai",
    )

    assert isinstance(content, list)
    assert content[0]["type"] == "text"
    assert content[1] == {
        "type": "file",
        "file": {
            "file_url": "https://example.com/egypt-reader.pdf",
            "filename": "egypt-reader.pdf",
        },
    }
