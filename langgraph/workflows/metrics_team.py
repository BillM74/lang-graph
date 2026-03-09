"""
Metrics Team workflow — metric definition, implementation, and validation.

Phases:
1. Metric Definition (metrics-analyst) → 7-gate metric spec
2. Schema Design (data-architect, conditional) → new model if needed
3. Impact Analysis (impact-analyzer) → safety check
4. Implementation (dbt-engineer) → metric calculation + tests
5. Validation (metrics-analyst) → reconciliation
6. Learning (retrospective-analyst)

Corresponds to: teams/metrics-team.yml
"""

from typing import Literal

from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph

from ..agents.nodes import (
    create_data_architect,
    create_dbt_engineer,
    create_impact_analyzer,
    create_metrics_analyst,
    create_retrospective_analyst,
)
from ..state import MetricsWorkflowState
from ._helpers import (
    gather_prior_context,
    invoke_and_extract,
    make_blocked_response,
    parse_gates_passed,
    parse_impact_classification,
)


def metric_definition_phase(state: MetricsWorkflowState) -> dict:
    """Phase 1: Metrics Analyst defines the metric through 7 gates."""
    analyst = create_metrics_analyst()
    task = state.get("task_description", "")

    response = invoke_and_extract(analyst, [
        HumanMessage(content=(
            f"Define a SOMA-compliant metric for:\n\n{task}\n\n"
            f"Walk through the 7-gate workflow:\n"
            f"1. Uniqueness check — search existing metrics\n"
            f"2. Classification — atomic or compound\n"
            f"3. Definition — complete all template fields\n"
            f"4. Validation — checklist pass\n"
            f"5. Dependencies — activities/entities/components\n"
            f"6. Implementation plan — semantic layer or nets\n"
            f"7. Test plan\n\n"
            f"Determine if a new data model is needed or if existing models suffice."
        ))
    ])

    needs_new_model = "new model" in response.lower() or "create model" in response.lower()

    return {
        "messages": [HumanMessage(content=f"[Metric Definition Complete]\n{response}")],
        "current_phase": "definition",
        "needs_new_model": needs_new_model,
        "artifacts": [f"metric_definition: needs_new_model={needs_new_model}"],
    }


def schema_design_phase(state: MetricsWorkflowState) -> dict:
    """Phase 2 (conditional): Data Architect designs new model if needed."""
    architect = create_data_architect()
    prior = gather_prior_context(state)

    response = invoke_and_extract(architect, [
        HumanMessage(content=(
            f"Design a data model to support the metric definition below:\n\n"
            f"{prior}\n\n"
            f"Produce a SOMA-compliant design spec."
        ))
    ])

    return {
        "messages": [HumanMessage(content=f"[Schema Design Complete]\n{response}")],
        "current_phase": "schema_design",
        "artifacts": ["schema_design: complete"],
    }


def metric_impact_phase(state: MetricsWorkflowState) -> dict:
    """Phase 3: Impact analysis for the metric implementation."""
    analyzer = create_impact_analyzer()
    prior = gather_prior_context(state)

    response = invoke_and_extract(analyzer, [
        HumanMessage(content=(
            f"Analyze the impact of implementing this metric:\n\n"
            f"{prior}\n\n"
            f"Run the 5-gate analysis and classify as SAFE/CAUTION/DANGEROUS."
        ))
    ])

    classification = parse_impact_classification(response)
    return {
        "messages": [HumanMessage(content=f"[Metric Impact Analysis]\n{response}")],
        "current_phase": "impact_analysis",
        "impact_classification": classification,
        "artifacts": [f"metric_impact: {classification}"],
    }


def metric_implementation_phase(state: MetricsWorkflowState) -> dict:
    """Phase 4: dbt Engineer implements the metric."""
    engineer = create_dbt_engineer()
    prior = gather_prior_context(state)

    response = invoke_and_extract(engineer, [
        HumanMessage(content=(
            f"Implement the metric as defined:\n\n{prior}\n\n"
            f"Follow TDD: write tests first, implement, run 6 verification gates."
        ))
    ])

    return {
        "messages": [HumanMessage(content=f"[Metric Implementation]\n{response}")],
        "current_phase": "implementation",
        "all_gates_passed": parse_gates_passed(response),
        "artifacts": [f"metric_implementation: gates_passed={parse_gates_passed(response)}"],
    }


def metric_validation_phase(state: MetricsWorkflowState) -> dict:
    """Phase 5: Metrics Analyst validates the implemented metric."""
    analyst = create_metrics_analyst()
    prior = gather_prior_context(state)

    response = invoke_and_extract(analyst, [
        HumanMessage(content=(
            f"Validate the implemented metric:\n\n{prior}\n\n"
            f"Validation process:\n"
            f"1. Calculate the metric from source of truth\n"
            f"2. Compare with the implemented metric output\n"
            f"3. Identify variance (must be <1% to pass)\n"
            f"4. If variance detected, identify root cause\n"
            f"5. Document findings"
        ))
    ])

    passed = "pass" in response.lower() and "fail" not in response.lower()

    return {
        "messages": [HumanMessage(content=f"[Metric Validation]\n{response}")],
        "current_phase": "validation",
        "validation_passed": passed,
        "artifacts": [f"metric_validation: passed={passed}"],
    }


def metric_learning_phase(state: MetricsWorkflowState) -> dict:
    """Phase 6: Retrospective analysis."""
    analyst = create_retrospective_analyst()
    prior = gather_prior_context(state)

    response = invoke_and_extract(analyst, [
        HumanMessage(content=(
            f"Retrospective for metrics workflow:\n\n{prior}\n\n"
            f"Analyze successes, failures, and extract learnings."
        ))
    ])

    return {
        "messages": [HumanMessage(content=f"[Metrics Retrospective]\n{response}")],
        "current_phase": "learning",
        "retrospective_summary": response,
        "status": "complete",
        "artifacts": ["metrics_retrospective: complete"],
    }


def blocked_node(state: MetricsWorkflowState) -> dict:
    """Terminal node for blocked metrics workflows."""
    return make_blocked_response("dangerous impact classification")


# --- Routing ---


def route_after_definition(
    state: MetricsWorkflowState,
) -> Literal["schema_design", "impact_analysis"]:
    """Route to schema design if new model needed, else straight to impact."""
    if state.get("needs_new_model", False):
        return "schema_design"
    return "impact_analysis"


def route_after_impact(
    state: MetricsWorkflowState,
) -> Literal["implementation", "blocked"]:
    """Route based on impact classification."""
    if state.get("impact_classification") == "dangerous":
        return "blocked"
    return "implementation"


def route_after_validation(
    state: MetricsWorkflowState,
) -> Literal["learning", "implementation"]:
    """Route back to implementation if validation fails."""
    if state.get("validation_passed", False):
        return "learning"
    return "implementation"


# --- Graph builder ---


def build_metrics_workflow() -> StateGraph:
    """Build the metrics team StateGraph.

    Flow:
        definition → (needs_model → schema_design → impact, else → impact)
        → impact → (safe/caution → implementation, dangerous → blocked)
        → implementation → validation → (passed → learning, failed → implementation)
        → learning → END
    """
    workflow = StateGraph(MetricsWorkflowState)

    workflow.add_node("definition", metric_definition_phase)
    workflow.add_node("schema_design", schema_design_phase)
    workflow.add_node("impact_analysis", metric_impact_phase)
    workflow.add_node("implementation", metric_implementation_phase)
    workflow.add_node("validation", metric_validation_phase)
    workflow.add_node("learning", metric_learning_phase)
    workflow.add_node("blocked", blocked_node)

    workflow.set_entry_point("definition")

    workflow.add_conditional_edges(
        "definition",
        route_after_definition,
        {"schema_design": "schema_design", "impact_analysis": "impact_analysis"},
    )
    workflow.add_edge("schema_design", "impact_analysis")
    workflow.add_conditional_edges(
        "impact_analysis",
        route_after_impact,
        {"implementation": "implementation", "blocked": "blocked"},
    )
    workflow.add_edge("implementation", "validation")
    workflow.add_conditional_edges(
        "validation",
        route_after_validation,
        {"learning": "learning", "implementation": "implementation"},
    )
    workflow.add_edge("learning", END)
    workflow.add_edge("blocked", END)

    return workflow.compile()
