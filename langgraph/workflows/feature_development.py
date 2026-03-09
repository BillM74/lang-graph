"""
Feature Development workflow — the primary multi-agent workflow.

Phases:
1. Design (data-architect) → design spec
2. Impact Analysis (impact-analyzer) → safe/caution/dangerous
3. Implementation (dbt-engineer) → built models with tests
4. Validation (dbt-code-reviewer)
5. Learning (retrospective-analyst)

Corresponds to: teams/feature-development.yml
"""

from typing import Literal

from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph

from ..agents.nodes import (
    create_data_architect,
    create_dbt_code_reviewer,
    create_dbt_engineer,
    create_impact_analyzer,
    create_retrospective_analyst,
)
from ..state import FeatureDevelopmentState
from ._helpers import (
    gather_prior_context,
    invoke_and_extract,
    make_blocked_response,
    parse_gates_passed,
    parse_impact_classification,
)


# --- Node functions ---


def design_phase(state: FeatureDevelopmentState) -> dict:
    """Phase 1: Data Architect designs the model spec."""
    architect = create_data_architect()
    task = state.get("task_description", "")
    response = invoke_and_extract(architect, [
        HumanMessage(content=(
            f"Design a SOMA-compliant data model for the following requirement:\n\n"
            f"{task}\n\n"
            f"Produce a complete design spec including: model name, SOMA layer, grain, "
            f"primary key, columns, materialization, incremental strategy, clustering keys, "
            f"dependencies, required tests, and description.\n\n"
            f"Use the Tree of Thought approach: evaluate 2-3 alternatives and score them "
            f"against Scalability (0.25), Maintainability (0.25), SOMA Compliance (0.30), "
            f"Performance (0.20). Design must score ≥75."
        ))
    ])

    return {
        "messages": [HumanMessage(content=f"[Design Phase Complete]\n{response}")],
        "current_phase": "design",
        "design_approved": True,
        "artifacts": [f"design_spec: {response[:200]}..."],
    }


def impact_analysis_phase(state: FeatureDevelopmentState) -> dict:
    """Phase 2: Impact Analyzer checks for downstream breaking changes."""
    analyzer = create_impact_analyzer()
    task = state.get("task_description", "")
    prior = gather_prior_context(state)

    response = invoke_and_extract(analyzer, [
        HumanMessage(content=(
            f"Analyze the downstream impact of the following proposed change:\n\n"
            f"Task: {task}\n\n"
            f"Design context from previous phase:\n{prior}\n\n"
            f"Run the 5-gate analysis:\n"
            f"1. Classify the change type (additive/mutative/removal)\n"
            f"2. Trace downstream consumers\n"
            f"3. Detect value-dependent filters\n"
            f"4. Check for dimension source collisions\n"
            f"5. Produce impact assessment (SAFE/CAUTION/DANGEROUS)"
        ))
    ])

    classification = parse_impact_classification(response)
    return {
        "messages": [HumanMessage(content=f"[Impact Analysis Complete]\n{response}")],
        "current_phase": "impact_analysis",
        "impact_classification": classification,
        "artifacts": [f"impact: {classification}"],
    }


def implementation_phase(state: FeatureDevelopmentState) -> dict:
    """Phase 3: dbt Engineer implements the model using TDD."""
    engineer = create_dbt_engineer()
    task = state.get("task_description", "")
    prior = gather_prior_context(state)

    response = invoke_and_extract(engineer, [
        HumanMessage(content=(
            f"Implement the following dbt model using Test-Driven Development:\n\n"
            f"Task: {task}\n\n"
            f"Context from design and impact analysis:\n{prior}\n\n"
            f"Follow TDD workflow:\n"
            f"1. Write tests FIRST (schema.yml)\n"
            f"2. Implement SQL model\n"
            f"3. Run all 6 verification gates:\n"
            f"   - dbt compile (no errors)\n"
            f"   - dbt run (model builds)\n"
            f"   - dbt test (all tests pass)\n"
            f"   - Documentation (grain + PK documented)\n"
            f"   - Downstream (no breaking changes)\n"
            f"   - Functional (semantic validation)\n"
        ))
    ])

    return {
        "messages": [HumanMessage(content=f"[Implementation Complete]\n{response}")],
        "current_phase": "implementation",
        "all_gates_passed": parse_gates_passed(response),
        "artifacts": [f"implementation: gates_passed={parse_gates_passed(response)}"],
    }


def review_phase(state: FeatureDevelopmentState) -> dict:
    """Phase 4: Code review by dbt-code-reviewer."""
    reviewer = create_dbt_code_reviewer()
    prior = gather_prior_context(state)

    response = invoke_and_extract(reviewer, [
        HumanMessage(content=(
            f"Review the following implementation:\n\n"
            f"{prior}\n\n"
            f"Apply the quality rubric (70/100 to pass):\n"
            f"- Readability (0.25)\n"
            f"- Testing (0.30, MUST pass)\n"
            f"- Documentation (0.20)\n"
            f"- SOMA Compliance (0.25)\n\n"
            f"Provide feedback using categories: 🔴 BLOCKING, 🟡 SUGGESTION, "
            f"🔵 QUESTION, ✅ PRAISE.\n"
            f"Include auto-fix code for any blocking issues.\n"
            f"Conclude with decision: APPROVED / CHANGES_REQUESTED / NEEDS_REWORK."
        ))
    ])

    # Parse decision
    lower = response.lower()
    if "approved" in lower and "needs_rework" not in lower and "changes_requested" not in lower:
        decision = "approved"
    elif "needs_rework" in lower:
        decision = "needs_rework"
    else:
        decision = "changes_requested"

    cycle = state.get("review_cycle", 0) + 1

    return {
        "messages": [HumanMessage(content=f"[Review Phase - Cycle {cycle}]\n{response}")],
        "current_phase": "review",
        "review_decision": decision,
        "review_cycle": cycle,
        "artifacts": [f"review_cycle_{cycle}: {decision}"],
    }


def fix_phase(state: FeatureDevelopmentState) -> dict:
    """Fix phase: Engineer addresses review findings."""
    engineer = create_dbt_engineer()

    review_messages = [
        m.content for m in state.get("messages", [])
        if isinstance(m, HumanMessage) and "Review Phase" in m.content
    ]
    latest_review = review_messages[-1] if review_messages else "No review findings"

    response = invoke_and_extract(engineer, [
        HumanMessage(content=(
            f"Fix the following code review findings:\n\n"
            f"{latest_review}\n\n"
            f"Apply all blocking fixes and suggested improvements.\n"
            f"Re-run all 6 verification gates after fixes."
        ))
    ])

    return {
        "messages": [HumanMessage(content=f"[Fixes Applied]\n{response}")],
        "current_phase": "fix",
        "artifacts": ["fixes_applied"],
    }


def learning_phase(state: FeatureDevelopmentState) -> dict:
    """Phase 5: Retrospective analysis."""
    analyst = create_retrospective_analyst()
    prior = gather_prior_context(state)

    response = invoke_and_extract(analyst, [
        HumanMessage(content=(
            f"Perform a retrospective analysis of this completed workflow:\n\n"
            f"{prior}\n\n"
            f"Analyze across 4 dimensions:\n"
            f"1. What went well (successes)\n"
            f"2. What could improve (failures/friction)\n"
            f"3. Discoveries and new patterns\n"
            f"4. Root causes of any issues\n\n"
            f"Produce a retrospective summary with actionable learnings."
        ))
    ])

    return {
        "messages": [HumanMessage(content=f"[Retrospective Complete]\n{response}")],
        "current_phase": "learning",
        "retrospective_summary": response,
        "status": "complete",
        "artifacts": ["retrospective: complete"],
    }


# --- Routing functions ---


def route_after_impact(
    state: FeatureDevelopmentState,
) -> Literal["implementation", "blocked"]:
    """Route based on impact classification."""
    if state.get("impact_classification", "safe") == "dangerous":
        return "blocked"
    return "implementation"


def route_after_review(
    state: FeatureDevelopmentState,
) -> Literal["learning", "fix", "blocked"]:
    """Route based on review decision and cycle count."""
    decision = state.get("review_decision", "approved")
    cycle = state.get("review_cycle", 0)

    if decision == "approved":
        return "learning"
    elif decision == "needs_rework" or cycle >= 3:
        return "blocked"
    else:
        return "fix"


def blocked_node(state: FeatureDevelopmentState) -> dict:
    """Terminal node for blocked workflows."""
    reason = state.get("impact_classification", "")
    if not reason or reason == "safe":
        reason = f"Review failed after {state.get('review_cycle', 0)} cycles"
    return make_blocked_response(reason)


# --- Graph builder ---


def build_feature_development_workflow() -> StateGraph:
    """Build the feature development StateGraph.

    Flow:
        design → impact_analysis → (safe/caution → implementation, dangerous → blocked)
        → implementation → review → (approved → learning, changes_requested → fix → review,
        needs_rework/max_cycles → blocked) → learning → END
    """
    workflow = StateGraph(FeatureDevelopmentState)

    workflow.add_node("design", design_phase)
    workflow.add_node("impact_analysis", impact_analysis_phase)
    workflow.add_node("implementation", implementation_phase)
    workflow.add_node("review", review_phase)
    workflow.add_node("fix", fix_phase)
    workflow.add_node("learning", learning_phase)
    workflow.add_node("blocked", blocked_node)

    workflow.set_entry_point("design")

    workflow.add_edge("design", "impact_analysis")
    workflow.add_conditional_edges(
        "impact_analysis",
        route_after_impact,
        {"implementation": "implementation", "blocked": "blocked"},
    )
    workflow.add_edge("implementation", "review")
    workflow.add_conditional_edges(
        "review",
        route_after_review,
        {"learning": "learning", "fix": "fix", "blocked": "blocked"},
    )
    workflow.add_edge("fix", "review")
    workflow.add_edge("learning", END)
    workflow.add_edge("blocked", END)

    return workflow.compile()
