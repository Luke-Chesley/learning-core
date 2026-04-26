from learning_core.contracts.operation import AppContext, PresentationContext, UserAuthoredContext
from learning_core.contracts.topic_suggestions import TopicSuggestArtifact
from learning_core.runtime.context import RuntimeContext
from learning_core.skills.topic_suggest.scripts.main import TopicSuggestSkill


def _context() -> RuntimeContext:
    return RuntimeContext.create(
        operation_name="topic_suggest",
        request_id="test-topic-suggest",
        app_context=AppContext(product="homeschool-v2", surface="curriculum"),
        presentation_context=PresentationContext(audience="parent"),
        user_authored_context=UserAuthoredContext(),
    )


def test_topic_suggest_prompt_includes_typo_query_and_local_suggestions():
    skill = TopicSuggestSkill()
    payload = skill.input_model.model_validate(
        {
            "query": "eurpoean histroy",
            "learner": "a 6th grader",
            "timeframe": "this week",
            "local_suggestions": ["European history"],
            "max_suggestions": 6,
        }
    )

    prompt = skill.build_user_prompt(payload, _context())

    assert "eurpoean histroy" in prompt
    assert "a 6th grader" in prompt
    assert "European history" in prompt


def test_topic_suggest_artifact_dedupes_and_trims_suggestions():
    artifact = TopicSuggestArtifact.model_validate(
        {
            "suggestions": [
                "insect life cycles",
                {"topic": " European history. "},
                {"topic": "European history"},
                {"topic": "medieval European history"},
            ]
        }
    )

    assert [suggestion.topic for suggestion in artifact.suggestions] == [
        "insect life cycles",
        "European history",
        "medieval European history",
    ]
