"""
Shared helpers for workflow phase functions.

Eliminates duplicated patterns across workflow files.
"""

from langchain_core.messages import BaseMessage, HumanMessage


def gather_prior_context(state: dict) -> str:
    """Extract context from previous phase messages in state."""
    return "\n".join(
        m.content for m in state.get("messages", [])
        if isinstance(m, HumanMessage) and "[" in m.content
    )


def invoke_and_extract(agent, messages: list[BaseMessage]) -> str:
    """Invoke an agent and return the last message content."""
    result = agent.invoke({"messages": messages})
    return result["messages"][-1].content if result["messages"] else ""


def parse_impact_classification(text: str) -> str:
    """Parse SAFE/CAUTION/DANGEROUS from agent response text."""
    lower = text.lower()
    if "dangerous" in lower:
        return "dangerous"
    elif "caution" in lower:
        return "caution"
    return "safe"


def parse_gates_passed(text: str) -> bool:
    """Parse whether verification gates passed from agent response text."""
    return "all gates passed" in text.lower() or "6/6" in text


def make_blocked_response(reason: str) -> dict:
    """Create a standard blocked state update."""
    return {
        "messages": [HumanMessage(content=f"[BLOCKED] Workflow blocked. Reason: {reason}")],
        "status": "blocked",
        "artifacts": [f"blocked: {reason}"],
    }
