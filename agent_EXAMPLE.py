"""
agent.py — Builds and runs the agent.

We use LangChain's `create_agent`, which implements the standard
tool-calling loop (Reason + Act):

  1. Model receives messages + system prompt
  2. Model either responds OR emits tool call(s)
  3. If tool calls: execute them, inject results, go to step 2
  4. If no tool calls: return the text response

`create_agent` handles the loop automatically. We just hand it
a model and a list of tools.

The agent is stateless — it doesn't hold conversation history itself.
We track history in main.py and pass the full message list on every turn.
"""

import os
from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, ToolMessage

from argostrator.tools import TOOLS
from argostrator.session import _text


def _build_react_agent(llm, tools, system_prompt: str):
    """
    Build an agent using the langchain create_agent API.
    """
    return create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
    )


def build_agent(system_prompt: str):
    """
    Create the agent.

    The system_prompt is injected via `system_prompt`.

    Model is read from ANTHROPIC_MODEL env var, defaulting to
    claude-sonnet-4-6. Set it in your .env to change it.
    """
    model_id = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    print("using model: ", {model_id})
    # Use explicit parameter names that match current langchain-anthropic typing.
    llm = ChatAnthropic(
        model_name=model_id,
        max_tokens_to_sample=4096,
        timeout=None,
        stop=None,
    )

    agent = _build_react_agent(llm, TOOLS, system_prompt)
    return agent


def run_turn(agent, messages: list, session=None, turn_index: int | None = None) -> tuple[str, list]:
    """
    Run one user turn through the agent and return the response.

    Returns:
        response_text  — the final assistant reply as a plain string
        new_messages   — the full updated message list (pass this back
                         next turn to maintain conversation history)

    We use agent.stream() with stream_mode="values" so we can print
    tool activity as it happens, without running the agent twice.
    """
    prev_len = len(messages)
    if session is not None and turn_index is not None:
        session.log_turn_input(turn_index, messages)

    step_index = 0
    color_enabled = os.getenv("NO_COLOR") is None
    c_tool = "\033[0;33m" if color_enabled else ""
    c_reset = "\033[0m" if color_enabled else ""

    for state in agent.stream({"messages": messages}, stream_mode="values"):
        final_state = state
        current = state["messages"]
        added = current[prev_len:]

        if session is not None and turn_index is not None:
            session.log_stream_step(turn_index, step_index, added)

        # Print any new messages added this step
        for msg in added:
            if isinstance(msg, AIMessage):
                for tc in getattr(msg, "tool_calls", []):
                    args_str = _format_args(tc["args"])
                    print(f"{c_tool}  → {tc['name']}({args_str}){c_reset}", flush=True)
            elif isinstance(msg, ToolMessage):
                preview = str(msg.content)[:120].replace("\n", " ")
                print(f"{c_tool}  ← {preview}{c_reset}", flush=True)

        prev_len = len(current)
        step_index += 1

    if final_state is None:
        raise RuntimeError("Agent returned no stream states.")

    new_messages = final_state["messages"]
    response = _text(new_messages[-1].content)
    response = _finalize_response_with_tools(response, new_messages)
    if session is not None and turn_index is not None:
        session.log_turn_output(turn_index, response, len(new_messages))
    return response, new_messages


def _finalize_response_with_tools(response: str, messages: list) -> str:
    """Finalize response with tool outputs from the current user turn."""
    if not messages:
        return response

    last_human_index = None
    for idx in range(len(messages) - 1, -1, -1):
        if messages[idx].__class__.__name__ == "HumanMessage":
            last_human_index = idx
            break

    if last_human_index is None:
        return response

    tool_messages = [
        msg for msg in messages[last_human_index + 1 :]
        if isinstance(msg, ToolMessage)
    ]

    if not tool_messages:
        return response

    # If a clarification was requested, return only the clarification block.
    for msg in tool_messages:
        if getattr(msg, "name", None) == "clarify_question":
            return str(msg.content or "").strip()

    tool_contents = []
    for msg in tool_messages:
        content = str(msg.content or "").strip()
        if content:
            tool_contents.append(content)

    if not tool_contents:
        return response

    blocks = []
    for content in tool_contents:
        if content[:80] in response:
            continue
        if len(content) > 4000:
            content = content[:4000].rstrip() + "\n... [truncated]"
        blocks.append(f"Result:\n{content}")

    if not blocks:
        return response

    return "\n\n".join(blocks) + "\n\n" + response


def _format_args(args: dict) -> str:
    """Format tool call arguments for display, capped at 60 chars per value."""
    parts = []
    for k, v in args.items():
        v_str = repr(v)
        if len(v_str) > 60:
            v_str = v_str[:57] + "..."
        parts.append(f"{k}={v_str}")
    return ", ".join(parts)
