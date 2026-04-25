from learning_core.contracts.curriculum import CurriculumRevisionTurn
from learning_core.skills.curriculum_revise.scripts.main import CurriculumReviseSkill


def test_curriculum_revise_repairs_legacy_document_shape_into_flat_skill_catalog():
    skill = CurriculumReviseSkill()
    raw_artifact = {
        "assistantMessage": "Applied the requested revision.",
        "action": "apply",
        "changeSummary": ["Added recipe work to the curriculum."],
        "artifact": {
            "source": {
                "title": "Kitchen Skills",
                "description": "A cooking curriculum.",
                "subjects": ["Practical Life"],
                "gradeLevels": ["Early Elementary"],
                "summary": "A cooking curriculum.",
                "teachingApproach": "Hands-on.",
                "successSignals": ["Learner completes simple recipes."],
                "parentNotes": [],
                "rationale": ["Recipes should live inside the curriculum."],
            },
            "intakeSummary": "Add recipe work.",
            "pacing": {
                "coverageStrategy": "Keep the original flow and add recipes after foundations.",
                "coverageNotes": [],
            },
            "document": {
                "Montessori Foundations": {
                    "Readiness": {
                        "Core ideas": ["Use real tools"],
                    }
                }
            },
            "Simple Recipes From the Book": {
                "No-Cook Recipes": {
                    "First dishes": ["Assemble a simple snack"],
                }
            },
            "units": [
                {
                    "unitRef": "unit-foundations",
                    "title": "Foundations",
                    "description": "Build readiness.",
                    "skillRefs": ["skill:montessori-foundations/readiness/core-ideas/use-real-tools"],
                },
                {
                    "unitRef": "unit-recipes",
                    "title": "Recipes",
                    "description": "Apply the skills in recipes.",
                    "skillRefs": [
                        "skill:simple-recipes-from-the-book/no-cook-recipes/first-dishes/assemble-a-simple-snack"
                    ],
                },
            ],
        },
    }

    repaired = skill.repair_invalid_artifact(
        raw_artifact=raw_artifact,
        payload=None,
        context=None,
        error=ValueError("artifact.Simple Recipes From the Book extra field"),
    )

    assert repaired is not None
    validated = CurriculumRevisionTurn.model_validate(repaired)
    assert validated.artifact is not None
    assert [skill.title for skill in validated.artifact.skills] == [
        "Use real tools",
        "Assemble a simple snack",
    ]
    assert validated.artifact.units[0].skillIds == ["skill-1"]
    assert validated.artifact.units[1].skillIds == ["skill-2"]
