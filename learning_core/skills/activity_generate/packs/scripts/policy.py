from learning_core.runtime.policy import ExecutionPolicy
from learning_core.skills.activity_generate.packs.scripts.tooling import BASE_ALLOWED_TOOLS

ACTIVITY_GENERATE_POLICY = ExecutionPolicy(
    skill_name="activity_generate",
    skill_version="2026-04-09",
    temperature=0.2,
    max_tokens=4096,
    allowed_tools=BASE_ALLOWED_TOOLS,
    max_attempts=1,
)
