from learning_core.runtime.policy import ExecutionPolicy

ACTIVITY_GENERATE_POLICY = ExecutionPolicy(
    skill_name="activity_generate",
    skill_version="2026-04-08",
    temperature=0.2,
    max_tokens=4096,
    allowed_tools=(),
    max_attempts=1,
)

