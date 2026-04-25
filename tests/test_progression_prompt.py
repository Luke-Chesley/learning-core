from learning_core.contracts.operation import AppContext, PresentationContext, UserAuthoredContext
import pytest
from pydantic import ValidationError

from learning_core.contracts.progression import ProgressionArtifact, ProgressionGenerationRequest
from learning_core.runtime.context import RuntimeContext
from learning_core.skills.progression_generate.scripts.main import ProgressionGenerateSkill


def _context():
    return RuntimeContext.create(
        operation_name="progression_generate",
        app_context=AppContext(product="homeschool-v2", surface="curriculum"),
        presentation_context=PresentationContext(audience="internal", display_intent="preview"),
        user_authored_context=UserAuthoredContext(),
    )


def _payload():
    return ProgressionGenerationRequest.model_validate(
        {
            "learnerName": "Ed",
            "sourceTitle": "Kitchen Skills",
            "sourceSummary": "A practical life sequence.",
            "requestMode": "source_entry",
            "sourceKind": "comprehensive_source",
            "deliveryPattern": "mixed",
            "entryStrategy": "section_start",
            "continuationMode": "sequential",
            "gradeLevels": ["preschool", "elementary"],
            "learnerPriorKnowledge": "unknown",
            "totalWeeks": 12,
            "sessionsPerWeek": 5,
            "sessionMinutes": 30,
            "totalSessions": 60,
            "suggestedPhaseCountMin": 5,
            "suggestedPhaseCountMax": 8,
            "skillCatalog": [
                {
                    "skillRef": "skill:kitchen/foundations/knife-safety",
                    "title": "Knife safety",
                    "domainTitle": "Kitchen",
                    "strandTitle": "Foundations",
                    "goalGroupTitle": "Safety",
                    "ordinal": 1,
                    "unitRef": "unit:1:safe-setup",
                    "unitTitle": "Safe setup",
                    "unitOrderIndex": 1,
                    "instructionalRole": "safety",
                    "requiresAdultSupport": True,
                    "safetyCritical": True,
                    "isAuthenticApplication": False,
                },
                {
                    "skillRef": "skill:kitchen/application/make-snack",
                    "title": "Make snack",
                    "domainTitle": "Kitchen",
                    "strandTitle": "Application",
                    "goalGroupTitle": "Recipes",
                    "ordinal": 2,
                    "unitRef": "unit:2:first-task",
                    "unitTitle": "First task",
                    "unitOrderIndex": 2,
                    "instructionalRole": "application",
                    "requiresAdultSupport": False,
                    "safetyCritical": False,
                    "isAuthenticApplication": True,
                },
            ],
            "unitAnchors": [
                {
                    "unitRef": "unit:1:safe-setup",
                    "title": "Safe setup",
                    "description": "Prepare the space and establish safety expectations.",
                    "orderIndex": 1,
                    "estimatedWeeks": 2,
                    "estimatedSessions": 8,
                    "skillRefs": ["skill:kitchen/foundations/knife-safety"],
                },
                {
                    "unitRef": "unit:2:first-task",
                    "title": "First task",
                    "description": "Move into authentic snack preparation.",
                    "orderIndex": 2,
                    "estimatedWeeks": 1,
                    "estimatedSessions": 4,
                    "skillRefs": ["skill:kitchen/application/make-snack"],
                },
            ],
        }
    )


def test_progression_prompt_includes_pacing_and_phase_budget_guidance():
    prompt = ProgressionGenerateSkill().build_user_prompt(_payload(), _context())

    assert "Pacing + phase-budget guidance:" in prompt
    assert "- Total weeks: 12" in prompt
    assert "- Sessions per week: 5" in prompt
    assert "- Session minutes: 30" in prompt
    assert "- Total sessions: 60" in prompt
    assert "- Suggested phase-count range: 5 to 8" in prompt


def test_progression_prompt_includes_unit_descriptions_and_estimates():
    prompt = ProgressionGenerateSkill().build_user_prompt(_payload(), _context())

    assert 'description: "Prepare the space and establish safety expectations."' in prompt
    assert "estimatedWeeks: 2" in prompt
    assert "estimatedSessions: 8" in prompt


def test_progression_prompt_includes_instructional_roles_and_flags():
    prompt = ProgressionGenerateSkill().build_user_prompt(_payload(), _context())

    assert 'instructionalRole: "safety"' in prompt
    assert "requiresAdultSupport: yes" in prompt
    assert "safetyCritical: yes" in prompt
    assert "isAuthenticApplication: yes" in prompt


def test_progression_prompt_requires_verbatim_skill_ref_copying():
    prompt = ProgressionGenerateSkill().build_user_prompt(_payload(), _context())

    assert 'EXACT skillRef: "skill:kitchen/foundations/knife-safety"' in prompt
    assert "copy this exact skillRef string verbatim anywhere it appears in phases or edges" in prompt
    assert "The only acceptable skillRef strings in the output are the exact strings printed above after \"EXACT skillRef:\"" in prompt
    assert "Do not reconstruct, normalize, shorten, prepend, append, or rewrite a skillRef" in prompt
    assert "the only acceptable output is an exact verbatim copy of a provided skillRef" in prompt


def test_progression_prompt_forbids_review_phase_duplicate_membership():
    prompt = ProgressionGenerateSkill().build_user_prompt(_payload(), _context())

    assert "Do not create a review, transfer, or capstone phase by repeating skillRefs" in prompt
    assert "Represent review, retrieval, fluency, and later practice with revisitAfter edges" in prompt


def test_progression_repair_removes_duplicate_skill_refs_from_later_phases():
    raw_artifact = {
        "phases": [
            {
                "title": "Foundations",
                "description": "Start with safety.",
                "skillRefs": ["skill:kitchen/foundations/knife-safety"],
            },
            {
                "title": "Application",
                "description": "Apply the routine.",
                "skillRefs": ["skill:kitchen/application/make-snack"],
            },
            {
                "title": "Review and transfer",
                "description": "Review the full routine.",
                "skillRefs": [
                    "skill:kitchen/foundations/knife-safety",
                    "skill:kitchen/application/make-snack",
                ],
            },
        ],
        "edges": [
            {
                "fromSkillRef": "skill:kitchen/foundations/knife-safety",
                "toSkillRef": "skill:kitchen/application/make-snack",
                "kind": "hardPrerequisite",
            }
        ],
    }

    repaired = ProgressionGenerateSkill().repair_invalid_artifact(
        raw_artifact=raw_artifact,
        payload=_payload(),
        context=_context(),
        error=ValueError("duplicate skillRef"),
    )

    artifact = ProgressionArtifact.model_validate(repaired)
    assert [phase.title for phase in artifact.phases] == ["Foundations", "Application"]


def test_progression_artifact_rejects_duplicate_edge_pairs_with_different_kinds():
    with pytest.raises(ValidationError):
        ProgressionArtifact.model_validate(
            {
                "phases": [
                    {
                        "title": "Foundations",
                        "description": "Start with safety.",
                        "skillRefs": ["skill:kitchen/foundations/knife-safety"],
                    },
                    {
                        "title": "Application",
                        "description": "Apply the routine.",
                        "skillRefs": ["skill:kitchen/application/make-snack"],
                    },
                ],
                "edges": [
                    {
                        "fromSkillRef": "skill:kitchen/foundations/knife-safety",
                        "toSkillRef": "skill:kitchen/application/make-snack",
                        "kind": "hardPrerequisite",
                    },
                    {
                        "fromSkillRef": "skill:kitchen/foundations/knife-safety",
                        "toSkillRef": "skill:kitchen/application/make-snack",
                        "kind": "recommendedBefore",
                    },
                ],
            }
        )


def test_progression_repair_recovers_uniquely_shortened_skill_refs():
    payload = ProgressionGenerationRequest.model_validate(
        {
            **_payload().model_dump(mode="json"),
            "skillCatalog": [
                {
                    "skillRef": "skill:recipe-use-and-measurement/reading-and-following-simple-recipe-cards/recipe-navigation/read-and-follow-simple-breakfast-recipe-cards-with-support",
                    "title": "Read recipe cards",
                },
                {
                    "skillRef": "skill:recipe-use-and-measurement/measuring-ingredients/measurement-basics/measure-dry-ingredients-accurately-using-common-kitchen-tools",
                    "title": "Measure dry ingredients",
                },
            ],
            "unitAnchors": [],
        }
    )
    raw_artifact = {
        "phases": [
            {
                "title": "Recipe basics",
                "description": "Start with cards.",
                "skillRefs": [
                    "skill:recipe-use-and-measurement/reading-and-following-simple-breakfast-recipe-cards-with-support"
                ],
            },
            {
                "title": "Measurement",
                "description": "Measure ingredients.",
                "skillRefs": [
                    "skill:recipe-use-and-measurement/measuring-ingredients/measurement-basics/measure-dry-ingredients-accurately-using-common-kitchen-tools"
                ],
            },
        ],
        "edges": [
            {
                "fromSkillRef": "skill:recipe-use-and-measurement/reading-and-following-simple-breakfast-recipe-cards-with-support",
                "toSkillRef": "skill:recipe-use-and-measurement/measuring-ingredients/measurement-basics/measure-dry-ingredients-accurately-using-common-kitchen-tools",
                "kind": "recommendedBefore",
            }
        ],
    }

    repaired = ProgressionGenerateSkill().repair_invalid_artifact(
        raw_artifact=raw_artifact,
        payload=payload,
        context=_context(),
        error=ValueError("invented skillRef"),
    )
    artifact = ProgressionArtifact.model_validate(repaired)

    expected = payload.skillCatalog[0].skillRef
    assert artifact.phases[0].skillRefs == [expected]
    assert artifact.edges[0].fromSkillRef == expected


def test_progression_semantic_validation_detects_missing_and_invented_skill_refs():
    raw_artifact = ProgressionArtifact.model_validate(
        {
            "phases": [
                {
                    "title": "Foundations",
                    "description": "Start with safety.",
                    "skillRefs": ["skill:kitchen/foundations/knife-safety"],
                },
                {
                    "title": "Application",
                    "description": "Apply the routine.",
                    "skillRefs": ["skill:kitchen/application/rewritten-make-snack"],
                },
            ],
            "edges": [],
        }
    )

    issues = ProgressionGenerateSkill().validate_artifact_semantics(
        artifact=raw_artifact,
        payload=_payload(),
        context=_context(),
    )

    assert any("progression missing skillRefs" in issue for issue in issues)
    assert any("progression invented skillRefs" in issue for issue in issues)


def test_progression_validation_retry_mentions_revisit_edges():
    preview = ProgressionGenerateSkill().build_validation_retry_preview(
        payload=_payload(),
        context=_context(),
        raw_artifact={
            "phases": [
                {
                    "title": "Review",
                    "description": "Repeat skills.",
                    "skillRefs": ["skill:kitchen/foundations/knife-safety"],
                }
            ],
            "edges": [],
        },
        error=ValueError("duplicate skillRef"),
    )

    assert "Each provided skillRef must appear in exactly one" in preview.user_prompt
    assert "add a revisitAfter edge instead of duplicating" in preview.user_prompt
