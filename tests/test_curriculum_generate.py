from __future__ import annotations

import pytest

from learning_core.contracts.curriculum import CurriculumArtifact, CurriculumGenerationRequest
from learning_core.contracts.operation import AppContext, PresentationContext, UserAuthoredContext
from learning_core.runtime.context import RuntimeContext
from learning_core.skills.curriculum_generate.scripts.main import CurriculumGenerateSkill


def _source_entry_payload() -> CurriculumGenerationRequest:
    return CurriculumGenerationRequest.model_validate(
        {
            "learnerName": "Maya",
            "titleCandidate": "Ancient Egypt",
            "requestMode": "source_entry",
            "requestedRoute": "outline",
            "routedRoute": "outline",
            "sourceKind": "comprehensive_source",
            "entryStrategy": "section_start",
            "entryLabel": "chapter 1",
            "continuationMode": "sequential",
            "deliveryPattern": "concept_first",
            "recommendedHorizon": "one_week",
            "sourceText": "Chapter 1 introduces the Nile and early settlements.",
            "sourcePackages": [
                {
                    "id": "ipkg-1",
                    "title": "Ancient Egypt reader",
                    "modality": "pdf",
                    "summary": "PDF reader about ancient Egypt",
                    "extractionStatus": "ready",
                    "assetCount": 1,
                    "assetIds": ["asset-1"],
                    "detectedChunks": ["Chapter 1", "Chapter 2"],
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
                    "fileData": "data:application/pdf;base64,ZmFrZS1wZGY=",
                }
            ],
            "detectedChunks": ["Chapter 1", "Chapter 2"],
            "assumptions": ["Start with the first chapter."],
        }
    )


def _conversation_payload() -> CurriculumGenerationRequest:
    return CurriculumGenerationRequest.model_validate(
        {
            "learnerName": "Maya",
            "titleCandidate": "Fractions this summer",
            "requestMode": "conversation_intake",
            "messages": [
                {
                    "role": "user",
                    "content": "Teach my daughter fractions this summer with three short sessions per week.",
                }
            ],
            "granularityGuidance": ["Keep the first week immediately teachable."],
            "correctionNotes": ["Prefer visual models before procedures."],
        }
    )


def _context() -> RuntimeContext:
    return RuntimeContext.create(
        operation_name="curriculum_generate",
        app_context=AppContext(product="homeschool-v2", surface="curriculum"),
        presentation_context=PresentationContext(),
        user_authored_context=UserAuthoredContext(),
    )


def test_curriculum_generate_prompt_preview_mentions_source_entry_fields():
    preview = CurriculumGenerateSkill().build_prompt_preview(_source_entry_payload(), _context())

    assert "Request mode: source_entry" in preview.user_prompt
    assert "Source kind: comprehensive_source" in preview.user_prompt
    assert "Delivery pattern: concept_first" in preview.user_prompt
    assert "Attached source files:" in preview.user_prompt
    assert "egypt-reader.pdf" in preview.user_prompt
    assert "Primary source text:" in preview.user_prompt


def test_curriculum_generate_prompt_preview_mentions_conversation_fields():
    preview = CurriculumGenerateSkill().build_prompt_preview(_conversation_payload(), _context())

    assert "Request mode: conversation_intake" in preview.user_prompt
    assert "Conversation transcript:" in preview.user_prompt
    assert "Teach my daughter fractions this summer" in preview.user_prompt
    assert "Granularity guidance:" in preview.user_prompt
    assert "Correction notes for this retry:" in preview.user_prompt
    assert "Requested route:" not in preview.user_prompt
    assert "Routed route:" not in preview.user_prompt


def test_curriculum_generate_builds_openai_file_message_blocks_for_source_entry():
    content = CurriculumGenerateSkill().build_user_message_content(
        _source_entry_payload(),
        _context(),
        provider="openai",
    )

    assert isinstance(content, list)
    assert content[0]["type"] == "text"
    assert content[1] == {
        "type": "input_file",
        "filename": "egypt-reader.pdf",
        "file_data": "data:application/pdf;base64,ZmFrZS1wZGY=",
    }


def test_curriculum_generate_builds_openai_image_message_blocks_for_source_entry():
    payload_data = _source_entry_payload().model_dump()
    payload_data["sourceFiles"] = [
        {
            "assetId": "asset-1",
            "packageId": "ipkg-1",
            "title": "Ancient Egypt worksheet",
            "modality": "image",
            "fileName": "egypt-worksheet.png",
            "mimeType": "image/png",
            "fileData": "data:image/png;base64,ZmFrZS1pbWFnZQ==",
        }
    ]
    payload = CurriculumGenerationRequest.model_validate(payload_data)

    content = CurriculumGenerateSkill().build_user_message_content(
        payload,
        _context(),
        provider="openai",
    )

    assert isinstance(content, list)
    assert content[0]["type"] == "text"
    assert content[1] == {
        "type": "input_image",
        "image_url": "data:image/png;base64,ZmFrZS1pbWFnZQ==",
    }


def test_curriculum_generate_builds_openai_file_url_message_blocks_for_source_entry():
    payload_data = _source_entry_payload().model_dump()
    payload_data["sourceFiles"] = [
        {
            "assetId": "asset-1",
            "packageId": "ipkg-1",
            "title": "Ancient Egypt reader",
            "modality": "pdf",
            "fileName": "egypt-reader.pdf",
            "mimeType": "application/pdf",
            "fileUrl": "https://example.com/egypt-reader.pdf",
        }
    ]
    payload = CurriculumGenerationRequest.model_validate(payload_data)

    content = CurriculumGenerateSkill().build_user_message_content(
        payload,
        _context(),
        provider="openai",
    )

    assert isinstance(content, list)
    assert content[0]["type"] == "text"
    assert content[1] == {
        "type": "input_file",
        "file_url": "https://example.com/egypt-reader.pdf",
    }


def test_curriculum_generate_does_not_attach_files_for_conversation_mode():
    content = CurriculumGenerateSkill().build_user_message_content(
        _conversation_payload(),
        _context(),
        provider="openai",
    )

    assert isinstance(content, str)
    assert "Conversation transcript:" in content


def test_curriculum_generate_rejects_source_fields_in_conversation_mode():
    with pytest.raises(ValueError):
        CurriculumGenerationRequest.model_validate(
            {
                "learnerName": "Maya",
                "requestMode": "conversation_intake",
                "messages": [{"role": "user", "content": "Teach fractions."}],
                "sourceText": "This should not be allowed.",
            }
        )


def test_curriculum_generate_rejects_route_fields_in_conversation_mode():
    with pytest.raises(ValueError):
        CurriculumGenerationRequest.model_validate(
            {
                "learnerName": "Maya",
                "requestMode": "conversation_intake",
                "requestedRoute": "topic",
                "messages": [{"role": "user", "content": "Teach fractions."}],
            }
        )


def _artifact_payload():
    return {
        "source": {
            "title": "Fractions Foundations",
            "description": "Desc",
            "summary": "Summary",
            "teachingApproach": "Approach",
        },
        "intakeSummary": "Summary",
        "pacing": {
            "coverageStrategy": "Strategy",
        },
        "skills": [
            {
                "skillId": "skill-1",
                "domainTitle": "Fractions",
                "strandTitle": "Concrete Fraction Sense",
                "goalGroupTitle": "Comparing and relating simple fractions",
                "title": "Compare fractions with the same denominator",
            },
            {
                "skillId": "skill-2",
                "domainTitle": "Fractions",
                "strandTitle": "Concrete Fraction Sense",
                "goalGroupTitle": "Comparing and relating simple fractions",
                "title": "Explain why two fourths equals one half",
            },
        ],
        "units": [
            {
                "unitRef": "unit:1:compare",
                "title": "Compare simple fractions",
                "description": "Desc",
                "skillIds": ["skill-1", "skill-2"],
            },
        ],
    }


def test_curriculum_artifact_accepts_flat_skill_catalog():
    artifact = CurriculumArtifact.model_validate(_artifact_payload())

    assert [skill.skillId for skill in artifact.skills] == ["skill-1", "skill-2"]
    assert artifact.units[0].skillIds == ["skill-1", "skill-2"]


def test_curriculum_artifact_rejects_unknown_unit_skill_ids():
    payload = _artifact_payload()
    payload["units"][0]["skillIds"] = ["skill-1", "missing-skill"]

    with pytest.raises(ValueError, match="unknown skillIds"):
        CurriculumArtifact.model_validate(payload)


def test_curriculum_artifact_rejects_duplicate_skill_paths():
    payload = _artifact_payload()
    payload["skills"].append(
        {
            "skillId": "skill-3",
            "domainTitle": "Fractions",
            "strandTitle": "Concrete Fraction Sense",
            "goalGroupTitle": "Comparing and relating simple fractions",
            "title": "Compare fractions with the same denominator",
        }
    )

    with pytest.raises(ValueError, match="duplicate skill paths"):
        CurriculumArtifact.model_validate(payload)


def test_curriculum_artifact_allows_leaf_titles_with_slashes():
    payload = _artifact_payload()
    payload["skills"][0]["title"] = "Read home/away patterns in a season schedule"

    artifact = CurriculumArtifact.model_validate(payload)
    assert artifact.skills[0].title == "Read home/away patterns in a season schedule"


def test_curriculum_artifact_rejects_zero_estimated_sessions():
    payload = _artifact_payload()
    payload["units"][0]["estimatedSessions"] = 0

    with pytest.raises(ValueError, match="estimatedSessions"):
        CurriculumArtifact.model_validate(payload)
