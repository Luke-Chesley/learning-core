"""
agent.py — Lightweight ReAct agent helper for skill-local tool-calling loops.

Wraps LangChain's create_agent() to run a tool-calling loop to completion
and return structured results for observability.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import BaseTool


@dataclass(frozen=True)
class ToolCallEvent:
    """A single tool call made during the agent loop."""

    tool_name: str
    tool_args: dict[str, Any]
    tool_output: str


@dataclass(frozen=True)
class AgentResult:
    """Result of a completed agent loop."""

    final_text: str
    tool_calls: list[ToolCallEvent]
    messages: list[Any] = field(repr=False)


def run_agent_loop(
    *,
    llm: Any,
    system_prompt: str,
    user_prompt: str,
    tools: Sequence[BaseTool | Callable[..., Any]],
    max_steps: int = 10,
) -> AgentResult:
    """
    Run a tool-calling ReAct loop to completion.

    Args:
        llm: A LangChain chat model instance.
        system_prompt: System instructions for the agent.
        user_prompt: The user's request.
        tools: Tools available to the agent.
        max_steps: Maximum number of tool-calling round trips.

    Returns:
        AgentResult with final text, tool call events, and full message history.
    """
    agent = create_agent(
        model=llm,
        tools=list(tools),
        system_prompt=system_prompt,
    )

    # Each tool-use round is 2 graph nodes (model call + tool execution).
    # Add 2 for the initial input and the final text-only model call.
    recursion_limit = max_steps * 2 + 2

    result = agent.invoke(
        {"messages": [HumanMessage(content=user_prompt)]},
        config={"recursion_limit": recursion_limit},
    )

    messages = result["messages"]

    # Pair AIMessage tool_calls with their ToolMessage responses.
    tool_call_events: list[ToolCallEvent] = []
    pending: dict[str, tuple[str, dict[str, Any]]] = {}

    for msg in messages:
        if isinstance(msg, AIMessage):
            for tc in getattr(msg, "tool_calls", []):
                pending[tc["id"]] = (tc["name"], tc["args"])
        elif isinstance(msg, ToolMessage):
            call_id = getattr(msg, "tool_call_id", None)
            if call_id and call_id in pending:
                name, args = pending.pop(call_id)
                tool_call_events.append(
                    ToolCallEvent(
                        tool_name=name,
                        tool_args=args,
                        tool_output=str(msg.content),
                    )
                )

    # Final text is the content of the last AIMessage.
    final_text = ""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and not getattr(msg, "tool_calls", None):
            content = msg.content
            if isinstance(content, list):
                final_text = "".join(
                    item.get("text", "") if isinstance(item, dict) else str(item)
                    for item in content
                )
            else:
                final_text = str(content)
            break

    return AgentResult(
        final_text=final_text,
        tool_calls=tool_call_events,
        messages=messages,
    )
