"""
Learning Team workflow — retrospective analysis and pattern extraction.

Single-agent team (retrospective-analyst) with 3 phases:
1. Analysis — examine artifacts, identify successes/failures
2. Pattern Extraction — store learnings, validate 2+ instances
3. Process Improvement — evidence-based proposals

Corresponds to: teams/learning-team.yml
"""

from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph

from ..agents.nodes import create_retrospective_analyst
from ..state import LearningWorkflowState
from ._helpers import gather_prior_context, invoke_and_extract


def analysis_phase(state: LearningWorkflowState) -> dict:
    """Phase 1: Analyze the completed workflow."""
    analyst = create_retrospective_analyst()
    task = state.get("task_description", "")

    response = invoke_and_extract(analyst, [
        HumanMessage(content=(
            f"Analyze the following completed workflow:\n\n{task}\n\n"
            f"Examine across 4 dimensions:\n"
            f"1. Successes — what worked well\n"
            f"2. Failures — what didn't work or caused friction\n"
            f"3. Discoveries — new patterns or insights\n"
            f"4. Root causes — underlying reasons for issues"
        ))
    ])

    return {
        "messages": [HumanMessage(content=f"[Analysis Complete]\n{response}")],
        "current_phase": "analysis",
        "artifacts": ["analysis: complete"],
    }


def pattern_extraction_phase(state: LearningWorkflowState) -> dict:
    """Phase 2: Extract and store patterns from the analysis."""
    analyst = create_retrospective_analyst()
    prior = gather_prior_context(state)

    response = invoke_and_extract(analyst, [
        HumanMessage(content=(
            f"Extract patterns from the analysis:\n\n{prior}\n\n"
            f"For each pattern:\n"
            f"- Name it descriptively\n"
            f"- Describe the context where it applies\n"
            f"- Document the pattern/anti-pattern\n"
            f"- Tag appropriately (pattern, reflection, episode)\n"
            f"- Note if this is a first occurrence or confirms existing pattern"
        ))
    ])

    return {
        "messages": [HumanMessage(content=f"[Patterns Extracted]\n{response}")],
        "current_phase": "pattern_extraction",
        "artifacts": ["patterns_extracted"],
    }


def improvement_proposal_phase(state: LearningWorkflowState) -> dict:
    """Phase 3: Propose process improvements (evidence-based only)."""
    analyst = create_retrospective_analyst()
    prior = gather_prior_context(state)

    response = invoke_and_extract(analyst, [
        HumanMessage(content=(
            f"Based on the analysis and patterns:\n\n{prior}\n\n"
            f"Propose process improvements ONLY if:\n"
            f"- The issue has occurred 2+ times (evidence-based)\n"
            f"- The improvement is specific and actionable\n"
            f"- The expected impact is clear\n\n"
            f"If no improvements meet the evidence threshold, say so explicitly.\n\n"
            f"Produce the final retrospective summary."
        ))
    ])

    return {
        "messages": [HumanMessage(content=f"[Retrospective Summary]\n{response}")],
        "current_phase": "proposals",
        "status": "complete",
        "artifacts": ["retrospective_summary: complete"],
    }


# --- Graph builder ---


def build_learning_workflow() -> StateGraph:
    """Build the learning team StateGraph.

    Flow: analysis → pattern_extraction → improvement_proposals → END
    """
    workflow = StateGraph(LearningWorkflowState)

    workflow.add_node("analysis", analysis_phase)
    workflow.add_node("pattern_extraction", pattern_extraction_phase)
    workflow.add_node("improvement_proposals", improvement_proposal_phase)

    workflow.set_entry_point("analysis")

    workflow.add_edge("analysis", "pattern_extraction")
    workflow.add_edge("pattern_extraction", "improvement_proposals")
    workflow.add_edge("improvement_proposals", END)

    return workflow.compile()
