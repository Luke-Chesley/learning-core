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
    assert "Scale guidance:" in preview.user_prompt
    assert "Planning constraints:" in preview.user_prompt
    assert "Attached source files:" in preview.user_prompt
    assert "egypt-reader.pdf" in preview.user_prompt
    assert "Primary source text:" in preview.user_prompt
    assert "Pacing contract:" in preview.user_prompt
    assert "Always emit positive integers for pacing.totalWeeks" in preview.user_prompt


def test_curriculum_generate_policy_has_room_for_session_sequence_artifacts():
    assert CurriculumGenerateSkill.policy.max_tokens >= 32000


def test_curriculum_generate_prompt_uses_planning_constraints_for_curriculum_request():
    payload = CurriculumGenerationRequest.model_validate(
        {
            **_source_entry_payload().model_dump(mode="json"),
            "sourceKind": "curriculum_request",
            "entryStrategy": "scaffold_only",
            "entryLabel": None,
            "continuationMode": "manual_review",
            "deliveryPattern": "mixed",
            "recommendedHorizon": "two_weeks",
            "sourceText": "Create a 30-session upper-elementary curriculum for a sample subject.",
            "detectedChunks": ["sample subject", "30 sessions"],
            "assumptions": ["No attached source files were provided."],
            "planningConstraints": {
                "totalSessions": 30,
                "gradeLevel": "4th grade",
                "learnerContext": "low prior knowledge",
                "practiceCadence": "daily bite-sized practice",
            },
        }
    )

    preview = CurriculumGenerateSkill().build_prompt_preview(payload, _context())

    assert "planningConstraints.totalSessions is 30" in preview.user_prompt
    assert "planningModel session_sequence" in preview.user_prompt
    assert "one concrete" in preview.user_prompt
    assert "Session sequence structural contract:" in preview.user_prompt
    assert "Treat IDs as a closed inventory" in preview.user_prompt
    assert "primary skillId and must be unique" in preview.user_prompt
    assert "Large exact-session artifact compactness contract:" in preview.user_prompt
    assert "Use exactly one primary skill, one content anchor, one teachable item, and one deliverySequence item per session" in preview.user_prompt
    assert '"totalSessions": 30' in preview.user_prompt
    assert '"gradeLevel": "4th grade"' in preview.user_prompt
    assert "Explicit planningConstraints to preserve: totalSessions=30" in preview.user_prompt


def test_curriculum_generate_prompt_infers_exact_sessions_from_source_entry_label():
    payload = CurriculumGenerationRequest.model_validate(
        {
            **_source_entry_payload().model_dump(mode="json"),
            "sourceKind": "curriculum_request",
            "entryStrategy": "timebox_start",
            "entryLabel": "30 sessions",
            "continuationMode": "timebox",
            "deliveryPattern": "mixed",
            "recommendedHorizon": "two_weeks",
            "sourceText": "I want to teach a 4th grader Maine history in 30 sessions.",
            "detectedChunks": ["4th grader Maine history", "30 sessions"],
            "assumptions": ["The 30 sessions are the explicit total delivery constraint."],
            "planningConstraints": None,
        }
    )

    preview = CurriculumGenerateSkill().build_prompt_preview(payload, _context())

    assert "planningConstraints.totalSessions is 30" in preview.user_prompt
    assert "Large exact-session artifact compactness contract:" in preview.user_prompt


def test_curriculum_generate_validation_retry_calls_out_unique_session_primary_skills():
    payload = CurriculumGenerationRequest.model_validate(
        {
            **_source_entry_payload().model_dump(mode="json"),
            "sourceKind": "curriculum_request",
            "deliveryPattern": "mixed",
            "sourceText": "Create a 5-session practical cooking curriculum.",
        }
    )

    preview = CurriculumGenerateSkill().build_validation_retry_preview(
        payload=payload,
        context=_context(),
        raw_artifact={"planningModel": "session_sequence", "deliverySequence": []},
        error=ValueError('planningModel "session_sequence" requires each deliverySequence item to use a unique primary skillId.'),
    )

    assert "unique first skillIds entry as its primary skillId" in preview.user_prompt
    assert "session-specific review, practice, application, or project skills" in preview.user_prompt
    assert "Treat IDs as a closed inventory" in preview.user_prompt


def test_curriculum_generate_prompt_preview_mentions_conversation_fields():
    preview = CurriculumGenerateSkill().build_prompt_preview(_conversation_payload(), _context())

    assert "Request mode: conversation_intake" in preview.user_prompt
    assert "Scale guidance:" in preview.user_prompt
    assert "Do not use planningModel session_sequence unless the conversation gives an exact session count" in preview.user_prompt
    assert "Conversation transcript:" in preview.user_prompt
    assert "Teach my daughter fractions this summer" in preview.user_prompt
    assert "Granularity guidance:" in preview.user_prompt
    assert "Correction notes for this retry:" in preview.user_prompt
    assert "Pacing contract:" in preview.user_prompt
    assert "Requested route:" not in preview.user_prompt
    assert "Routed route:" not in preview.user_prompt


def test_curriculum_generate_prompt_allows_scale_matched_hierarchy():
    preview = CurriculumGenerateSkill().build_prompt_preview(_conversation_payload(), _context())

    assert "Choose a curriculum scale" in preview.system_prompt
    assert "teachable content map" in preview.system_prompt
    assert "every artifact must include concrete `pacing.totalWeeks`" in preview.system_prompt
    assert "micro" in preview.system_prompt
    assert "week" in preview.system_prompt
    assert "Avoid generic skills" in preview.system_prompt


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
            "totalWeeks": 1,
            "sessionsPerWeek": 2,
            "sessionMinutes": 30,
            "totalSessions": 2,
            "coverageStrategy": "Strategy",
        },
        "curriculumScale": "module",
        "planningModel": "content_map",
        "skills": [
            {
                "skillId": "skill-1",
                "domainTitle": "Fractions",
                "strandTitle": "Concrete Fraction Sense",
                "goalGroupTitle": "Comparing and relating simple fractions",
                "title": "Compare fractions with the same denominator",
                "description": "Use fraction strips to compare thirds with thirds and fourths with fourths.",
                "contentAnchorIds": ["anchor-1"],
                "practiceCue": "Compare 2/4 and 3/4 with strips.",
                "assessmentCue": "Learner can explain that same denominators mean same-size pieces.",
            },
            {
                "skillId": "skill-2",
                "domainTitle": "Fractions",
                "strandTitle": "Concrete Fraction Sense",
                "goalGroupTitle": "Comparing and relating simple fractions",
                "title": "Explain why two fourths equals one half",
                "description": "Fold or shade four equal parts and show that two parts match one half.",
                "contentAnchorIds": ["anchor-2"],
                "practiceCue": "Shade two of four equal rectangles and compare with one half.",
                "assessmentCue": "Learner can match 2/4 to 1/2 with a visual model.",
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
        "contentAnchors": [
            {
                "anchorId": "anchor-1",
                "title": "Same denominator comparisons",
                "summary": "Fractions with the same denominator use equal-size parts, so compare numerators.",
                "details": ["Use thirds with thirds and fourths with fourths."],
                "sourceRefs": [{"label": "test source"}],
                "grounding": "source_grounded",
            },
            {
                "anchorId": "anchor-2",
                "title": "Two fourths equals one half",
                "summary": "Two of four equal parts covers the same amount as one of two equal parts.",
                "details": ["Use folded paper or strips."],
                "sourceRefs": [{"label": "test source"}],
                "grounding": "source_grounded",
            },
        ],
        "teachableItems": [
            {
                "itemId": "item-1",
                "unitRef": "unit:1:compare",
                "title": "Same-size pieces",
                "focusQuestion": "Why can we compare numerators when denominators match?",
                "contentAnchorIds": ["anchor-1"],
                "namedAnchors": ["thirds", "fourths", "numerator", "denominator"],
                "vocabulary": ["numerator", "denominator"],
                "learnerOutcome": "Learner compares same-denominator fractions with a model.",
                "assessmentCue": "Learner explains that the pieces are the same size.",
                "misconceptions": ["Comparing denominator size instead of piece count."],
                "parentNotes": ["Use strips before symbols."],
                "skillIds": ["skill-1"],
                "estimatedSessions": 1,
                "sourceRefs": [{"label": "test source"}],
            },
            {
                "itemId": "item-2",
                "unitRef": "unit:1:compare",
                "title": "Two fourths as one half",
                "focusQuestion": "How can two fourths cover the same amount as one half?",
                "contentAnchorIds": ["anchor-2"],
                "namedAnchors": ["half", "fourth", "equal parts"],
                "vocabulary": ["equivalent"],
                "learnerOutcome": "Learner shows 2/4 and 1/2 cover the same area.",
                "assessmentCue": "Learner matches 2/4 to 1/2 with a visual.",
                "misconceptions": ["Thinking 2/4 is bigger because 4 is bigger than 2."],
                "parentNotes": ["Fold paper into halves and fourths."],
                "skillIds": ["skill-2"],
                "estimatedSessions": 1,
                "sourceRefs": [{"label": "test source"}],
            },
        ],
        "deliverySequence": [],
        "sourceCoverage": [],
    }


def test_curriculum_artifact_accepts_flat_skill_catalog():
    artifact = CurriculumArtifact.model_validate(_artifact_payload())

    assert [skill.skillId for skill in artifact.skills] == ["skill-1", "skill-2"]
    assert artifact.units[0].skillIds == ["skill-1", "skill-2"]


def test_curriculum_artifact_accepts_week_scale_without_hierarchy_labels():
    artifact = CurriculumArtifact.model_validate(
        {
            "source": {
                "title": "Clouds This Week",
                "description": "Desc",
                "summary": "Summary",
                "teachingApproach": "Approach",
            },
            "intakeSummary": "A one-week cloud observation curriculum.",
            "pacing": {
                "totalWeeks": 1,
                "sessionsPerWeek": 4,
                "sessionMinutes": 20,
                "totalSessions": 4,
                "coverageStrategy": "Observe and classify common cloud types this week.",
            },
            "curriculumScale": "week",
            "planningModel": "content_map",
            "skills": [
                {
                    "skillId": "skill-1",
                    "title": "Observe cloud shape and height",
                    "description": "Look at cloud shape and whether clouds seem low or high.",
                    "contentAnchorIds": ["anchor-1"],
                    "practiceCue": "Sketch one cloud and describe its shape.",
                    "assessmentCue": "Learner can name one visible cloud feature.",
                },
                {
                    "skillId": "skill-2",
                    "title": "Match cloud observations to likely weather",
                    "description": "Connect dark or tall clouds with likely rain and flat fair-weather clouds with calmer weather.",
                    "contentAnchorIds": ["anchor-2"],
                    "practiceCue": "Match a cloud sketch to a weather guess.",
                    "assessmentCue": "Learner gives one observation-based weather guess.",
                },
            ],
            "units": [
                {
                    "unitRef": "unit:1:clouds-week",
                    "title": "Cloud observations",
                    "description": "A compact week of cloud observation.",
                    "estimatedWeeks": 1,
                    "estimatedSessions": 4,
                    "skillIds": ["skill-1", "skill-2"],
                }
            ],
            "contentAnchors": [
                {
                    "anchorId": "anchor-1",
                    "title": "Cloud shape and height",
                    "summary": "Clouds can be observed by shape and whether they look low, middle, or high.",
                    "details": [],
                    "sourceRefs": [{"label": "Cloud week"}],
                    "grounding": "model_suggested",
                },
                {
                    "anchorId": "anchor-2",
                    "title": "Clouds and weather clues",
                    "summary": "Some cloud observations can be used as simple clues about possible weather.",
                    "details": [],
                    "sourceRefs": [{"label": "Cloud week"}],
                    "grounding": "model_suggested",
                },
            ],
            "teachableItems": [
                {
                    "itemId": "item-1",
                    "unitRef": "unit:1:clouds-week",
                    "title": "Cloud observation walk",
                    "focusQuestion": "What do we notice about the cloud shape and height?",
                    "contentAnchorIds": ["anchor-1"],
                    "namedAnchors": ["shape", "height", "sky"],
                    "vocabulary": ["observe", "shape"],
                    "learnerOutcome": "Learner sketches one cloud and describes one feature.",
                    "assessmentCue": "Learner names a visible feature.",
                    "misconceptions": [],
                    "parentNotes": [],
                    "skillIds": ["skill-1"],
                    "estimatedSessions": 2,
                    "sourceRefs": [{"label": "Cloud week"}],
                },
                {
                    "itemId": "item-2",
                    "unitRef": "unit:1:clouds-week",
                    "title": "Cloud weather clue",
                    "focusQuestion": "What weather might this cloud suggest?",
                    "contentAnchorIds": ["anchor-2"],
                    "namedAnchors": ["rain", "fair weather", "dark cloud"],
                    "vocabulary": ["weather"],
                    "learnerOutcome": "Learner makes one weather guess from a cloud observation.",
                    "assessmentCue": "Learner connects the guess to an observation.",
                    "misconceptions": [],
                    "parentNotes": [],
                    "skillIds": ["skill-2"],
                    "estimatedSessions": 2,
                    "sourceRefs": [{"label": "Cloud week"}],
                },
            ],
            "deliverySequence": [
                {
                    "sequenceId": "session-1",
                    "position": 1,
                    "label": "Session 1",
                    "title": "Sketch cloud shape",
                    "sessionFocus": "Observe and sketch one cloud shape.",
                    "teachableItemId": "item-1",
                    "contentAnchorIds": ["anchor-1"],
                    "skillIds": ["skill-1"],
                    "estimatedMinutes": 20,
                    "evidenceToSave": ["Cloud sketch"],
                    "reviewOf": [],
                },
                {
                    "sequenceId": "session-2",
                    "position": 2,
                    "label": "Session 2",
                    "title": "Sort high and low clouds",
                    "sessionFocus": "Compare whether clouds look low or high.",
                    "teachableItemId": "item-1",
                    "contentAnchorIds": ["anchor-1"],
                    "skillIds": ["skill-1"],
                    "estimatedMinutes": 20,
                    "evidenceToSave": ["Observation note"],
                    "reviewOf": [],
                },
                {
                    "sequenceId": "session-3",
                    "position": 3,
                    "label": "Session 3",
                    "title": "Guess weather from clouds",
                    "sessionFocus": "Use cloud clues to make a simple weather guess.",
                    "teachableItemId": "item-2",
                    "contentAnchorIds": ["anchor-2"],
                    "skillIds": ["skill-2"],
                    "estimatedMinutes": 20,
                    "evidenceToSave": ["Weather guess note"],
                    "reviewOf": [],
                },
                {
                    "sequenceId": "session-4",
                    "position": 4,
                    "label": "Session 4",
                    "title": "Review cloud journal",
                    "sessionFocus": "Review sketches and choose the clearest weather clue.",
                    "teachableItemId": "item-2",
                    "contentAnchorIds": ["anchor-2"],
                    "skillIds": ["skill-2"],
                    "estimatedMinutes": 20,
                    "evidenceToSave": ["Cloud journal page"],
                    "reviewOf": ["Cloud shape and height"],
                },
            ],
            "sourceCoverage": [],
        }
    )

    assert artifact.curriculumScale == "week"
    assert artifact.skills[0].domainTitle is None
    assert artifact.skills[0].canonical_skill_ref() == (
        "skill:curriculum/core-sequence/focus-skills/observe-cloud-shape-and-height"
    )


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


def test_curriculum_artifact_requires_one_sequence_item_per_timeboxed_session():
    payload = _artifact_payload()
    payload["planningModel"] = "session_sequence"
    payload["pacing"]["totalSessions"] = 2
    payload["deliverySequence"] = [
        {
            "sequenceId": "session-1",
            "position": 1,
            "label": "Session 1",
            "title": "Compare same-denominator fractions",
            "sessionFocus": "Use strips to compare 2/4 and 3/4.",
            "teachableItemId": "item-1",
            "contentAnchorIds": ["anchor-1"],
            "skillIds": ["skill-1"],
            "estimatedMinutes": 20,
            "evidenceToSave": ["Marked fraction strip"],
            "reviewOf": [],
        }
    ]

    with pytest.raises(ValueError, match="one deliverySequence item per total session"):
        CurriculumArtifact.model_validate(payload)

    payload["deliverySequence"].append(
        {
            "sequenceId": "session-2",
            "position": 2,
            "label": "Session 2",
            "title": "Explain two fourths as one half",
            "sessionFocus": "Fold paper to match 2/4 and 1/2.",
            "teachableItemId": "item-2",
            "contentAnchorIds": ["anchor-2"],
            "skillIds": ["skill-2"],
            "estimatedMinutes": 20,
            "evidenceToSave": ["Folded paper model"],
            "reviewOf": ["same-denominator comparison"],
        }
    )

    artifact = CurriculumArtifact.model_validate(payload)
    assert [item.position for item in artifact.deliverySequence] == [1, 2]
