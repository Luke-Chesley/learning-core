from learning_core.contracts.operation import AppContext, PresentationContext, UserAuthoredContext
from learning_core.contracts.progression import ProgressionGenerationRequest
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
