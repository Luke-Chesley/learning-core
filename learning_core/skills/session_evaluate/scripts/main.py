from __future__ import annotations

from learning_core.contracts.evaluation import EvaluationArtifact, SessionEvaluationRequest
from learning_core.runtime.policy import ExecutionPolicy
from learning_core.skills.base import StructuredOutputSkill
from learning_core.skills.prompt_utils import append_user_authored_context


class SessionEvaluateSkill(StructuredOutputSkill):
    name = "session_evaluate"
    input_model = SessionEvaluationRequest
    output_model = EvaluationArtifact
    policy = ExecutionPolicy(
        skill_name="session_evaluate",
        skill_version="2026-04-20",
        max_tokens=4000,
    )

    def build_user_prompt(self, payload: SessionEvaluationRequest, context) -> str:
        evidence_lines = (
            "\n".join(
                f"- {item.source}: {item.summary}" + (f" (score={item.score})" if item.score is not None else "")
                for item in payload.evidence
            )
            if payload.evidence
            else "- No evidence supplied."
        )
        lines = [
            f"Session ID: {payload.sessionId}",
            f"Learner: {payload.learnerName}",
            f"Lesson title: {payload.lessonTitle}",
            "",
            "Evidence:",
            evidence_lines,
            "",
            "Use one of these exact ratings:",
            "- needs_more_work",
            "- partial",
            "- successful",
            "- exceeded",
            "",
            "Judgment rules:",
            "- Rate the session from the supplied evidence only.",
            "- If the evidence is thin or mixed, stay conservative.",
            "- Keep nextActions short and directly teachable by a parent or teacher.",
        ]
        append_user_authored_context(lines, context)
        lines.extend(["", "Return the evaluation artifact."])
        return "\n".join(lines)
