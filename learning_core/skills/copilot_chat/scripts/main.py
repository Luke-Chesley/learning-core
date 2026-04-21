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
        skill_version="2026-04-20",
        task_kind="chat",
        max_tokens=4096,
    )

    def build_user_prompt(self, payload: CopilotChatRequest, context) -> str:
        lines = [
            "Current app context:",
            payload.context.model_dump_json(indent=2) if payload.context else "No additional context provided.",
            "",
            "Supported Copilot actions:",
            '- planning.adjust_day_load -> move one weekly route item to a lighter date using ids from weeklyPlanningSnapshot.items.',
            '- planning.defer_or_move_item -> defer or reschedule one weekly route item using ids from weeklyPlanningSnapshot.items.',
            '- planning.generate_today_lesson -> queue or generate the lesson for a specific date already present in context.',
            "- tracking.record_note -> save one durable note tied to the learner, and optionally the current lesson session.",
            "",
            "Action constraints:",
            "- Return actions only when the context supports a safe, specific mutation.",
            "- Use only ids, dates, and route items that appear in the provided context.",
            "- Prefer an empty actions array over a speculative action.",
            "- Keep requiresApproval=true for meaningful mutations.",
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
        lines.extend(
            [
                "",
                "Reply to the latest parent message directly.",
                "Return a structured artifact with `answer` and `actions`.",
            ]
        )
        return "\n".join(lines)

    def execute(self, engine, payload: CopilotChatRequest, context) -> SkillExecutionResult[CopilotChatArtifact]:
        artifact, lineage, trace = engine.run_structured_output(
            skill=self,
            payload=payload,
            context=context,
        )
        return SkillExecutionResult(
            artifact=artifact,
            lineage=lineage,
            trace=trace,
        )
