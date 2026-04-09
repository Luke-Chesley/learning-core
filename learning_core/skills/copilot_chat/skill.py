from __future__ import annotations

from learning_core.contracts.copilot import CopilotChatArtifact, CopilotChatRequest
from learning_core.runtime.policy import ExecutionPolicy
from learning_core.runtime.skill import SkillExecutionResult
from learning_core.skills.base import StructuredOutputSkill
from learning_core.skills.prompt_utils import append_user_authored_context


class CopilotChatSkill(StructuredOutputSkill):
    name = "copilot_chat"
    input_model = CopilotChatRequest
    output_model = CopilotChatArtifact
    policy = ExecutionPolicy(
        skill_name="copilot_chat",
        skill_version="2026-04-09",
        task_kind="chat",
        max_tokens=4096,
    )

    def build_user_prompt(self, payload: CopilotChatRequest, context) -> str:
        lines = [
            "Current app context:",
            payload.context.model_dump_json(indent=2) if payload.context else "No additional context provided.",
            "",
            "Conversation:",
        ]

        if payload.messages:
            for message in payload.messages:
                speaker = "Assistant" if message.role == "assistant" else "Parent"
                lines.append(f"- {speaker}: {message.content}")
        else:
            lines.append("- Parent: Hello")

        append_user_authored_context(lines, context)
        lines.extend(["", "Reply to the latest parent message directly."])
        return "\n".join(lines)

    def execute(self, engine, payload: CopilotChatRequest, context) -> SkillExecutionResult[CopilotChatArtifact]:
        answer, lineage, trace = engine.run_text_output(
            skill=self,
            payload=payload,
            context=context,
        )
        return SkillExecutionResult(
            artifact=CopilotChatArtifact(answer=answer.strip()),
            lineage=lineage,
            trace=trace,
        )
