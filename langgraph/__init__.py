"""
LangGraph-based orchestration for SOMA analytics engineering workflows.

Converts Claude Code skills, agents, and teams into LangGraph workflows
that can run independently of the Claude Code CLI.

Usage:
    from langgraph.workflows.feature_development import build_feature_development_workflow
    from langgraph.workflows.metrics_team import build_metrics_workflow
    from langgraph.workflows.performance_team import build_performance_workflow
    from langgraph.workflows.learning_team import build_learning_workflow

    # Build and invoke a workflow
    workflow = build_feature_development_workflow()
    result = workflow.invoke({
        "task_description": "Create a new activity model for order_placed events",
        "messages": [],
    })
"""
