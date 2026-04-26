from __future__ import annotations

import json

from learning_core.contracts.topic_suggestions import TopicSuggestArtifact, TopicSuggestRequest
from learning_core.runtime.policy import ExecutionPolicy
from learning_core.skills.base import StructuredOutputSkill


class TopicSuggestSkill(StructuredOutputSkill):
    name = "topic_suggest"
    input_model = TopicSuggestRequest
    output_model = TopicSuggestArtifact
    policy = ExecutionPolicy(
        skill_name="topic_suggest",
        skill_version="2026-04-25",
        task_kind="chat",
        temperature=0.35,
        max_tokens=512,
        latency_class="interactive",
    )

    def build_user_prompt(self, payload: TopicSuggestRequest, context) -> str:
        lines = [
            f"Partial topic query: {payload.query}",
            f"Learner context: {payload.learner or 'not provided'}",
            f"Timeframe context: {payload.timeframe or 'not provided'}",
            f"Maximum suggestions: {payload.max_suggestions}",
            "",
            "Local suggestions already available:",
            json.dumps(payload.local_suggestions, indent=2),
            "",
            "Return concise topic completions or adjacent topic ideas as JSON matching the schema.",
        ]
        return "\n".join(lines)

    def repair_invalid_artifact(self, *, raw_artifact, payload, context, error):
        if isinstance(raw_artifact, list):
            return {
                "suggestions": [
                    {"topic": str(item)}
                    for item in raw_artifact
                    if str(item).strip()
                ][: payload.max_suggestions]
            }
        if isinstance(raw_artifact, dict):
            raw_suggestions = raw_artifact.get("suggestions")
            if isinstance(raw_suggestions, list):
                repaired = []
                for item in raw_suggestions:
                    if isinstance(item, str):
                        repaired.append({"topic": item})
                    elif isinstance(item, dict) and item.get("topic"):
                        repaired.append({"topic": item["topic"]})
                return {"suggestions": repaired[: payload.max_suggestions]}
        return None
