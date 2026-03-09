"""
Performance Team workflow — diagnose, optimize, validate, document.

Phases:
1. Diagnosis (performance-optimizer) → identify bottleneck + strategy
2. Implementation (dbt-engineer) → apply optimization
3. Validation (performance-optimizer A/B test + dbt-code-reviewer)
4. Learning (retrospective-analyst)

Corresponds to: teams/performance-team.yml
"""

from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph

from ..agents.nodes import (
    create_dbt_code_reviewer,
    create_dbt_engineer,
    create_performance_optimizer,
    create_retrospective_analyst,
)
from ..state import PerformanceWorkflowState
from ._helpers import gather_prior_context, invoke_and_extract


def diagnosis_phase(state: PerformanceWorkflowState) -> dict:
    """Phase 1: Performance Optimizer diagnoses the bottleneck."""
    optimizer = create_performance_optimizer()
    task = state.get("task_description", "")

    response = invoke_and_extract(optimizer, [
        HumanMessage(content=(
            f"Diagnose the following performance issue:\n\n{task}\n\n"
            f"Steps:\n"
            f"1. Gather performance metrics (query profile, bytes scanned, spillage)\n"
            f"2. Identify root cause (full scan, spillage, joins, windows)\n"
            f"3. Recommend optimization strategy\n"
            f"4. Record baseline metrics for A/B comparison\n\n"
            f"Use the performance decision tree to guide diagnosis."
        ))
    ])

    return {
        "messages": [HumanMessage(content=f"[Diagnosis Complete]\n{response}")],
        "current_phase": "diagnosis",
        "artifacts": ["diagnosis: complete"],
    }


def perf_implementation_phase(state: PerformanceWorkflowState) -> dict:
    """Phase 2: dbt Engineer applies the optimization."""
    engineer = create_dbt_engineer()
    prior = gather_prior_context(state)

    response = invoke_and_extract(engineer, [
        HumanMessage(content=(
            f"Apply the optimization recommended in the diagnosis:\n\n"
            f"{prior}\n\n"
            f"Implement changes and run all 6 verification gates."
        ))
    ])

    return {
        "messages": [HumanMessage(content=f"[Optimization Implemented]\n{response}")],
        "current_phase": "implementation",
        "artifacts": ["optimization_implemented"],
    }


def ab_test_phase(state: PerformanceWorkflowState) -> dict:
    """Phase 3a: Performance Optimizer runs A/B comparison."""
    optimizer = create_performance_optimizer()
    prior = gather_prior_context(state)

    response = invoke_and_extract(optimizer, [
        HumanMessage(content=(
            f"Run A/B comparison for the optimization:\n\n{prior}\n\n"
            f"Compare before/after:\n"
            f"- Runtime (seconds)\n"
            f"- Bytes scanned\n"
            f"- Credits used\n"
            f"- Spillage (bytes)\n"
            f"- Partition pruning ratio\n\n"
            f"Improvement must be >30% speed OR >30% cost reduction to pass."
        ))
    ])

    return {
        "messages": [HumanMessage(content=f"[A/B Test Results]\n{response}")],
        "current_phase": "ab_test",
        "artifacts": [f"ab_test: complete"],
    }


def perf_review_phase(state: PerformanceWorkflowState) -> dict:
    """Phase 3b: Code review of optimization changes."""
    reviewer = create_dbt_code_reviewer()
    prior = gather_prior_context(state)

    response = invoke_and_extract(reviewer, [
        HumanMessage(content=(
            f"Review the optimization changes:\n\n{prior}\n\n"
            f"Focus on: correctness, no regressions, SOMA compliance, testing."
        ))
    ])

    decision = "approved"
    if "changes_requested" in response.lower():
        decision = "changes_requested"
    elif "needs_rework" in response.lower():
        decision = "needs_rework"

    return {
        "messages": [HumanMessage(content=f"[Performance Review]\n{response}")],
        "review_decision": decision,
        "artifacts": [f"perf_review: {decision}"],
    }


def perf_learning_phase(state: PerformanceWorkflowState) -> dict:
    """Phase 4: Retrospective analysis."""
    analyst = create_retrospective_analyst()
    prior = gather_prior_context(state)

    response = invoke_and_extract(analyst, [
        HumanMessage(content=(
            f"Retrospective for performance optimization workflow:\n\n"
            f"{prior}\n\n"
            f"Document the optimization pattern for future reference."
        ))
    ])

    return {
        "messages": [HumanMessage(content=f"[Performance Retrospective]\n{response}")],
        "current_phase": "learning",
        "retrospective_summary": response,
        "status": "complete",
        "artifacts": ["perf_retrospective: complete"],
    }


# --- Graph builder ---


def build_performance_workflow() -> StateGraph:
    """Build the performance team StateGraph.

    Flow:
        diagnosis → implementation → ab_test → review → learning → END
    """
    workflow = StateGraph(PerformanceWorkflowState)

    workflow.add_node("diagnosis", diagnosis_phase)
    workflow.add_node("implementation", perf_implementation_phase)
    workflow.add_node("ab_test", ab_test_phase)
    workflow.add_node("review", perf_review_phase)
    workflow.add_node("learning", perf_learning_phase)

    workflow.set_entry_point("diagnosis")

    workflow.add_edge("diagnosis", "implementation")
    workflow.add_edge("implementation", "ab_test")
    workflow.add_edge("ab_test", "review")
    workflow.add_edge("review", "learning")
    workflow.add_edge("learning", END)

    return workflow.compile()
