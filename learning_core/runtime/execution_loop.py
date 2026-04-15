from __future__ import annotations

from learning_core.agent import run_agent_loop


def run_agentic_loop_with_adaptive_retry(
    *,
    llm,
    system_prompt: str,
    user_prompt: str,
    tools: list[object],
    initial_max_steps: int = 5,
    fallback_max_steps: int = 8,
):
    try:
        return run_agent_loop(
            llm=llm,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            tools=tools,
            max_steps=initial_max_steps,
        )
    except Exception as error:
        if "GRAPH_RECURSION_LIMIT" not in str(error):
            raise
        return run_agent_loop(
            llm=llm,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            tools=tools,
            max_steps=fallback_max_steps,
        )
