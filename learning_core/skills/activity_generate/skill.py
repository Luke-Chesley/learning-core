from __future__ import annotations

from learning_core.contracts.activity import ActivityArtifact, ActivityGenerationInput
from learning_core.runtime.context import RuntimeContext
from learning_core.skills.base import StructuredOutputSkill
from learning_core.skills.activity_generate.policy import ACTIVITY_GENERATE_POLICY

def _build_user_prompt(payload: ActivityGenerationInput, context: RuntimeContext) -> str:
    lesson = payload.lesson_draft
    lines: list[str] = []

    lines.append("## Activity generation request")
    lines.append("")
    learner_line = f"Learner: {payload.learner_name}"
    if payload.learner_grade_level:
        learner_line += f" ({payload.learner_grade_level})"
    lines.append(learner_line)
    lines.append(f"Subject: {payload.subject or 'General'}")
    lines.append(f"Session budget: {lesson.total_minutes} minutes")

    if payload.workflow_mode:
        lines.append(f"Workflow mode: {payload.workflow_mode}")
    elif context.app_context.workflow_mode:
        lines.append(f"Workflow mode: {context.app_context.workflow_mode}")

    lines.append("")
    lines.append("## Lesson plan")
    lines.append(f"Title: {lesson.title}")
    lines.append(f"Focus: {lesson.lesson_focus}")

    if lesson.primary_objectives:
        lines.append("Objectives:")
        for objective in lesson.primary_objectives:
            lines.append(f"- {objective}")

    if lesson.success_criteria:
        lines.append("Success criteria (use these as mastery indicators in teacherSupport):")
        for criterion in lesson.success_criteria:
            lines.append(f"- {criterion}")

    if lesson.blocks:
        lines.append("Lesson blocks:")
        for block in lesson.blocks:
            optional = " [optional]" if block.optional else ""
            lines.append(f"  [{block.type}{optional}] {block.title} ({block.minutes} min)")
            lines.append(f"    Purpose: {block.purpose}")
            lines.append(f"    Learner: {block.learner_action}")

    if lesson.materials:
        lines.append(f"Materials: {', '.join(lesson.materials)}")

    if lesson.teacher_notes:
        lines.append("Teacher notes:")
        for note in lesson.teacher_notes:
            lines.append(f"- {note}")

    if lesson.adaptations:
        lines.append("Adaptations:")
        for adaptation in lesson.adaptations:
            lines.append(f"- {adaptation.trigger}: {adaptation.action}")

    if lesson.assessment_artifact:
        lines.append(f"Assessment artifact: {lesson.assessment_artifact}")

    if lesson.lesson_shape:
        lines.append(f"Lesson shape: {lesson.lesson_shape}")

    lines.append("")
    lines.append(f'Activity scope: session - "{lesson.title}"')

    if payload.linked_objective_ids:
        lines.append("")
        lines.append("Linked objective IDs (use these in linkedObjectiveIds field):")
        lines.append(", ".join(payload.linked_objective_ids))

    if payload.linked_skill_titles:
        lines.append("")
        lines.append("Linked skill titles (use these in linkedSkillTitles field):")
        lines.append(", ".join(payload.linked_skill_titles))

    if payload.standard_ids:
        lines.append("")
        lines.append("Standard IDs in scope:")
        lines.append(", ".join(payload.standard_ids))

    if context.user_authored_context.parent_goal:
        lines.append("")
        lines.append(f"Parent goal: {context.user_authored_context.parent_goal}")

    if context.user_authored_context.note:
        lines.append("")
        lines.append(f"Parent note: {context.user_authored_context.note}")

    if context.user_authored_context.teacher_note:
        lines.append("")
        lines.append(f"Teacher note: {context.user_authored_context.teacher_note}")

    if context.user_authored_context.special_constraints:
        lines.append("")
        lines.append("Special constraints:")
        for value in context.user_authored_context.special_constraints:
            lines.append(f"- {value}")

    if context.user_authored_context.avoidances:
        lines.append("")
        lines.append("Avoid:")
        for value in context.user_authored_context.avoidances:
            lines.append(f"- {value}")

    if context.user_authored_context.custom_instruction:
        lines.append("")
        lines.append(f"Custom instruction: {context.user_authored_context.custom_instruction}")

    lines.append("")
    lines.append("Generate a single ActivitySpec JSON object. Do not include any text outside the JSON.")
    return "\n".join(lines)


class ActivityGenerateSkill(StructuredOutputSkill):
    name = "activity_generate"
    input_model = ActivityGenerationInput
    output_model = ActivityArtifact
    policy = ACTIVITY_GENERATE_POLICY

    def build_user_prompt(self, payload: ActivityGenerationInput, context: RuntimeContext) -> str:
        return _build_user_prompt(payload, context)
