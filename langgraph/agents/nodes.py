"""
Agent node factories for LangGraph workflows.

Each function creates a ReAct agent node with the appropriate
system prompt and tool set for its specialized role.
"""

from langchain_core.language_models import BaseChatModel
from langgraph.prebuilt import create_react_agent

from ..config import get_model
from ..prompts.system_prompts import (
    AGENT_ROUTER_PROMPT,
    DATA_ARCHITECT_PROMPT,
    DBT_CODE_REVIEWER_PROMPT,
    DBT_ENGINEER_PROMPT,
    IMPACT_ANALYZER_PROMPT,
    METRICS_ANALYST_PROMPT,
    PERFORMANCE_OPTIMIZER_PROMPT,
    PROJECT_MANAGER_PROMPT,
    RETROSPECTIVE_ANALYST_PROMPT,
)
from ..tools.dbt_tools import (
    dbt_build,
    dbt_compile,
    dbt_get_lineage,
    dbt_get_node_details,
    dbt_list_models,
    dbt_parse,
    dbt_run,
    dbt_show,
    dbt_test,
)
from ..tools.quality_tools import (
    analyze_impact,
    check_sql_quality,
    generate_test_yaml,
    review_code_changes,
    run_functional_tests,
)
from ..tools.snowflake_tools import (
    clustering_health_check,
    cost_breakdown,
    describe_snowflake_object,
    list_snowflake_objects,
    query_profile_analysis,
    run_snowflake_query,
    warehouse_spillage_check,
)
from ..tools.soma_tools import (
    check_metric_uniqueness,
    classify_soma_layer,
    define_metric,
    validate_metric,
    validate_soma_compliance,
)


def create_data_architect(model: BaseChatModel | None = None):
    """Create the Data Architect agent node.

    Tools: SOMA classification, validation, dbt lineage/parse, Snowflake describe.
    """
    llm = model or get_model()
    tools = [
        classify_soma_layer,
        validate_soma_compliance,
        dbt_parse,
        dbt_get_lineage,
        dbt_get_node_details,
        dbt_list_models,
        describe_snowflake_object,
        list_snowflake_objects,
    ]
    return create_react_agent(llm, tools, prompt=DATA_ARCHITECT_PROMPT)


def create_dbt_engineer(model: BaseChatModel | None = None):
    """Create the dbt Engineer agent node.

    Tools: All dbt operations, SQL quality, test generation, SOMA validation.
    """
    llm = model or get_model()
    tools = [
        dbt_compile,
        dbt_run,
        dbt_test,
        dbt_build,
        dbt_show,
        dbt_parse,
        dbt_get_lineage,
        dbt_get_node_details,
        dbt_list_models,
        check_sql_quality,
        generate_test_yaml,
        run_functional_tests,
        validate_soma_compliance,
        classify_soma_layer,
        run_snowflake_query,
    ]
    return create_react_agent(llm, tools, prompt=DBT_ENGINEER_PROMPT)


def create_dbt_code_reviewer(model: BaseChatModel | None = None):
    """Create the dbt Code Reviewer agent node.

    Tools: Code review, SQL quality, test generation, SOMA validation, dbt introspection.
    """
    llm = model or get_model()
    tools = [
        review_code_changes,
        check_sql_quality,
        generate_test_yaml,
        validate_soma_compliance,
        dbt_get_lineage,
        dbt_get_node_details,
        dbt_list_models,
        dbt_test,
        dbt_compile,
        run_functional_tests,
    ]
    return create_react_agent(llm, tools, prompt=DBT_CODE_REVIEWER_PROMPT)


def create_impact_analyzer(model: BaseChatModel | None = None):
    """Create the Impact Analyzer agent node.

    Tools: Impact analysis, dbt lineage, SOMA validation (read-only).
    """
    llm = model or get_model()
    tools = [
        analyze_impact,
        dbt_get_lineage,
        dbt_get_node_details,
        dbt_list_models,
        validate_soma_compliance,
        run_functional_tests,
    ]
    return create_react_agent(llm, tools, prompt=IMPACT_ANALYZER_PROMPT)


def create_metrics_analyst(model: BaseChatModel | None = None):
    """Create the Metrics Analyst agent node.

    Tools: Metric definition/validation, SOMA tools, Snowflake queries.
    """
    llm = model or get_model()
    tools = [
        define_metric,
        validate_metric,
        check_metric_uniqueness,
        classify_soma_layer,
        validate_soma_compliance,
        dbt_get_node_details,
        dbt_list_models,
        run_snowflake_query,
    ]
    return create_react_agent(llm, tools, prompt=METRICS_ANALYST_PROMPT)


def create_performance_optimizer(model: BaseChatModel | None = None):
    """Create the Performance Optimizer agent node.

    Tools: Snowflake diagnostics, dbt operations, SQL quality.
    """
    llm = model or get_model()
    tools = [
        query_profile_analysis,
        clustering_health_check,
        warehouse_spillage_check,
        cost_breakdown,
        run_snowflake_query,
        describe_snowflake_object,
        list_snowflake_objects,
        dbt_build,
        dbt_run,
        dbt_show,
        dbt_compile,
        check_sql_quality,
    ]
    return create_react_agent(llm, tools, prompt=PERFORMANCE_OPTIMIZER_PROMPT)


def create_project_manager(model: BaseChatModel | None = None):
    """Create the Project Manager agent node.

    Tools: dbt introspection, SOMA tools, metric definition.
    """
    llm = model or get_model()
    tools = [
        dbt_list_models,
        dbt_get_lineage,
        dbt_get_node_details,
        classify_soma_layer,
        validate_soma_compliance,
        define_metric,
    ]
    return create_react_agent(llm, tools, prompt=PROJECT_MANAGER_PROMPT)


def create_retrospective_analyst(model: BaseChatModel | None = None):
    """Create the Retrospective Analyst agent node.

    Tools: Minimal — this agent primarily produces text analysis.
    """
    llm = model or get_model()
    tools = []  # Retrospective agent works with messages, not tools
    return create_react_agent(llm, tools, prompt=RETROSPECTIVE_ANALYST_PROMPT)


def create_agent_router(model: BaseChatModel | None = None):
    """Create the Agent Router node for task classification.

    Tools: dbt introspection for context.
    """
    llm = model or get_model()
    tools = [
        dbt_list_models,
        dbt_get_lineage,
        dbt_get_node_details,
    ]
    return create_react_agent(llm, tools, prompt=AGENT_ROUTER_PROMPT)
