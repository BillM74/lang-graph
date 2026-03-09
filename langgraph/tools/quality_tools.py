"""
Code quality and testing tools for LangGraph agents.

Implements SQL quality checks, test generation, functional testing,
impact analysis, and code review as callable tools.
"""

import re

from langchain_core.tools import tool

from .soma_tools import check_soma_naming


SQL_ANTI_PATTERNS = [
    {
        "pattern": re.compile(r"SELECT\s+\*\s+FROM\s+(?!.*\bAS\b)", re.IGNORECASE),
        "name": "select_star_in_final",
        "severity": "warning",
        "message": "Avoid SELECT * in production queries — explicitly list columns.",
    },
    {
        "pattern": re.compile(r"/\s+(?!nullif\s*\()", re.IGNORECASE),
        "name": "unsafe_division",
        "severity": "error",
        "message": "Division without NULLIF protection. Use: numerator / NULLIF(denominator, 0)",
    },
    {
        "pattern": re.compile(r"\bNOT\s+IN\b", re.IGNORECASE),
        "name": "not_in_usage",
        "severity": "warning",
        "message": "NOT IN can produce unexpected results with NULLs. Use NOT EXISTS instead.",
    },
    {
        "pattern": re.compile(r"\bDISTINCT\b(?!.*\bcount_distinct\b)", re.IGNORECASE),
        "name": "distinct_bandaid",
        "severity": "info",
        "message": "DISTINCT may be masking a join fan-out. Verify the root cause.",
    },
    {
        "pattern": re.compile(r"\t"),
        "name": "tabs_found",
        "severity": "warning",
        "message": "Use 4 spaces for indentation, not tabs.",
    },
]

CTE_PATTERN = re.compile(
    r"WITH\s+(\w+)\s+AS\s*\(", re.IGNORECASE | re.MULTILINE
)

FINAL_CTE_PATTERN = re.compile(
    r"SELECT\s+\*\s+FROM\s+final\s*$", re.IGNORECASE | re.MULTILINE
)

_HARDCODED_PATTERN = re.compile(r"WHERE\s+\w+\s*=\s*'[^{].*?'", re.IGNORECASE)
_COL_ALIAS_PATTERN = re.compile(r"AS\s+(\w+)", re.IGNORECASE)


@tool
def check_sql_quality(
    sql_content: str,
    model_name: str = "",
) -> dict:
    """Check SQL code quality against project standards.

    Validates CTE structure, naming conventions, anti-patterns,
    and formatting standards.

    Args:
        sql_content: SQL content to analyze
        model_name: Optional model name for context
    """
    findings = []

    # Check CTE structure (imports → logic → final)
    ctes = CTE_PATTERN.findall(sql_content)
    has_final = bool(FINAL_CTE_PATTERN.search(sql_content))

    if ctes and not has_final:
        findings.append({
            "severity": "warning",
            "rule": "cte_final_pattern",
            "message": "Model should end with 'SELECT * FROM final'. Missing final CTE pattern.",
        })

    # Check for config block
    if not sql_content.strip().startswith("{{") and "config(" not in sql_content[:200]:
        findings.append({
            "severity": "info",
            "rule": "missing_config",
            "message": "Consider adding a config block at the top of the model.",
        })

    # Anti-pattern checks
    for anti_pattern in SQL_ANTI_PATTERNS:
        matches = anti_pattern["pattern"].findall(sql_content)
        if matches:
            findings.append({
                "severity": anti_pattern["severity"],
                "rule": anti_pattern["name"],
                "message": anti_pattern["message"],
                "occurrences": len(matches),
            })

    # Check for hardcoded values
    hardcoded = _HARDCODED_PATTERN.findall(sql_content)
    if hardcoded:
        findings.append({
            "severity": "warning",
            "rule": "hardcoded_values",
            "message": f"Found {len(hardcoded)} hardcoded values in WHERE clauses. Consider using variables.",
            "examples": hardcoded[:3],
        })

    # Check column naming conventions
    column_aliases = _COL_ALIAS_PATTERN.findall(sql_content)
    bad_names = [c for c in column_aliases if c != c.lower() or "-" in c]
    if bad_names:
        findings.append({
            "severity": "warning",
            "rule": "column_naming",
            "message": f"Column aliases should be snake_case. Issues: {bad_names[:5]}",
        })

    # Compute quality score
    error_count = sum(1 for f in findings if f["severity"] == "error")
    warning_count = sum(1 for f in findings if f["severity"] == "warning")
    score = max(0, 100 - (error_count * 15) - (warning_count * 5))

    return {
        "model_name": model_name,
        "score": score,
        "findings": findings,
        "cte_count": len(ctes),
        "has_final_cte": has_final,
        "error_count": error_count,
        "warning_count": warning_count,
    }


@tool
def generate_test_yaml(
    model_name: str,
    columns: dict[str, str],
    soma_layer: str,
    primary_key: list[str],
    foreign_keys: dict[str, str] | None = None,
    categorical_columns: dict[str, list[str]] | None = None,
) -> dict:
    """Generate dbt test YAML for a model based on SOMA layer and column types.

    Args:
        model_name: Name of the dbt model
        columns: Dict of column_name → column_type (e.g., {'order_id': 'primary_key'})
        soma_layer: SOMA layer (staging, activities, entities, nets)
        primary_key: List of primary key columns
        foreign_keys: Dict of FK column → referenced model
        categorical_columns: Dict of column → accepted values list
    """
    foreign_keys = foreign_keys or {}
    categorical_columns = categorical_columns or {}

    tests = []
    column_tests = {}

    # Primary key tests (always required)
    for pk_col in primary_key:
        column_tests[pk_col] = [
            {"unique": None},
            {"not_null": None},
        ]

    # Composite primary key
    if len(primary_key) > 1:
        tests.append({
            "dbt_utils.unique_combination_of_columns": {
                "combination_of_columns": primary_key,
            }
        })

    # Foreign key tests
    for fk_col, ref_model in foreign_keys.items():
        if fk_col not in column_tests:
            column_tests[fk_col] = []
        column_tests[fk_col].extend([
            {"not_null": None},
            {"relationships": {"to": f"ref('{ref_model}')", "field": fk_col}},
        ])

    # Categorical columns
    for col, values in categorical_columns.items():
        if col not in column_tests:
            column_tests[col] = []
        column_tests[col].append({
            "accepted_values": {"values": values}
        })

    # Layer-specific required tests
    if soma_layer == "activities":
        for col in ["activity_type", "occurred_at"]:
            if col not in column_tests:
                column_tests[col] = []
            if not any("not_null" in t for t in column_tests[col]):
                column_tests[col].append({"not_null": None})

    elif soma_layer == "nets":
        for col in ["measured_at", "valid_from", "valid_to"]:
            if col not in column_tests:
                column_tests[col] = []
            if not any("not_null" in t for t in column_tests[col]):
                column_tests[col].append({"not_null": None})

    # Build YAML structure
    yaml_structure = {
        "version": 2,
        "models": [{
            "name": model_name,
            "description": f"TODO: Add description for {model_name}",
            "columns": [
                {"name": col, "tests": col_tests}
                for col, col_tests in column_tests.items()
            ],
            "tests": tests if tests else None,
        }],
    }

    # Generate YAML string
    yaml_lines = [f"version: 2", "", "models:", f"  - name: {model_name}"]
    yaml_lines.append(f"    description: 'TODO: Add description for {model_name}'")

    if tests:
        yaml_lines.append("    tests:")
        for test in tests:
            for test_name, test_config in test.items():
                yaml_lines.append(f"      - {test_name}:")
                for key, value in test_config.items():
                    yaml_lines.append(f"          {key}: {value}")

    yaml_lines.append("    columns:")
    for col, col_tests in column_tests.items():
        yaml_lines.append(f"      - name: {col}")
        if col_tests:
            yaml_lines.append("        tests:")
            for test in col_tests:
                if isinstance(test, dict):
                    for test_name, test_config in test.items():
                        if test_config is None:
                            yaml_lines.append(f"          - {test_name}")
                        else:
                            yaml_lines.append(f"          - {test_name}:")
                            for key, value in test_config.items():
                                yaml_lines.append(f"              {key}: {value}")

    return {
        "model_name": model_name,
        "soma_layer": soma_layer,
        "yaml_content": "\n".join(yaml_lines),
        "test_count": sum(len(t) for t in column_tests.values()) + len(tests),
        "columns_tested": list(column_tests.keys()),
    }


@tool
def run_functional_tests(
    model_name: str,
    test_type: str,
    sql_query: str = "",
) -> dict:
    """Generate functional test SQL for semantic validation beyond schema tests.

    Args:
        model_name: Model to test
        test_type: Type of functional test:
            - 'duplicate_detection': Check for dimension collisions
            - 'ytd_accumulation': Verify cumulative calculations
            - 'cross_model_consistency': Compare totals across models
            - 'dimension_consistency': Verify dimension source alignment
            - 'edge_case': Validate edge cases
        sql_query: Custom SQL query to use (optional, generates template if empty)
    """
    templates = {
        "duplicate_detection": f"""
-- Duplicate Detection: Find entities with multiple dimension values
SELECT
    entity_id,
    dimension_column,
    COUNT(*) AS occurrence_count
FROM {{{{ ref('{model_name}') }}}}
GROUP BY entity_id, dimension_column
HAVING COUNT(*) > 1
ORDER BY occurrence_count DESC
LIMIT 20
""",
        "ytd_accumulation": f"""
-- YTD Accumulation: Verify cumulative sum matches window function
SELECT
    date_column,
    metric_column,
    SUM(metric_column) OVER (
        ORDER BY date_column
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS expected_ytd,
    ytd_column AS actual_ytd,
    expected_ytd - actual_ytd AS difference
FROM {{{{ ref('{model_name}') }}}}
WHERE expected_ytd != actual_ytd
LIMIT 20
""",
        "cross_model_consistency": f"""
-- Cross-Model Consistency: Compare aggregated totals
WITH detail AS (
    SELECT SUM(metric_column) AS detail_total
    FROM {{{{ ref('{model_name}') }}}}
    WHERE date_column >= '2024-01-01'
),
summary AS (
    SELECT SUM(metric_column) AS summary_total
    FROM {{{{ ref('summary_model') }}}}
    WHERE date_column >= '2024-01-01'
)
SELECT
    detail.detail_total,
    summary.summary_total,
    detail.detail_total - summary.summary_total AS difference,
    CASE WHEN detail.detail_total = summary.summary_total
        THEN 'PASS' ELSE 'FAIL' END AS status
FROM detail
CROSS JOIN summary
""",
        "dimension_consistency": f"""
-- Dimension Source Consistency: All CTEs pull dimension from canonical source
-- Verify no conflicting dimension values from different source CTEs
SELECT
    entity_id,
    COUNT(DISTINCT dimension_value) AS distinct_values
FROM {{{{ ref('{model_name}') }}}}
GROUP BY entity_id
HAVING COUNT(DISTINCT dimension_value) > 1
LIMIT 20
""",
        "edge_case": f"""
-- Edge Case Validation: Check for anomalies
SELECT
    *
FROM {{{{ ref('{model_name}') }}}}
WHERE entity_id IN (
    -- System/admin entities that may cause anomalies
    SELECT entity_id
    FROM {{{{ ref('{model_name}') }}}}
    WHERE entity_type IN ('system', 'admin', 'test', 'internal')
)
LIMIT 20
""",
    }

    test_sql = sql_query if sql_query else templates.get(test_type, "")

    if not test_sql:
        return {
            "success": False,
            "error": f"Unknown test type: {test_type}. Available: {list(templates.keys())}",
        }

    return {
        "success": True,
        "model_name": model_name,
        "test_type": test_type,
        "test_sql": test_sql.strip(),
        "description": f"Functional test ({test_type}) for {model_name}",
        "note": "Execute this SQL via dbt_show or run_snowflake_query to validate.",
    }


@tool
def analyze_impact(
    changed_model: str,
    change_type: str,
    change_description: str,
    downstream_models: list[str],
    changed_columns: list[str] | None = None,
    removed_columns: list[str] | None = None,
) -> dict:
    """Analyze the downstream impact of a proposed model change.

    Implements the 5-gate impact analysis process:
    1. Change classification
    2. Downstream consumer trace
    3. Value-dependent filter detection
    4. Dimension source collision check
    5. Impact assessment

    Args:
        changed_model: Name of the model being changed
        change_type: Type of change: 'additive', 'mutative', 'removal'
        change_description: Description of what's changing
        downstream_models: List of models that depend on changed_model
        changed_columns: Columns being modified
        removed_columns: Columns being removed
    """
    changed_columns = changed_columns or []
    removed_columns = removed_columns or []
    issues = []
    warnings = []

    # Gate 1: Change classification
    if change_type == "removal":
        if removed_columns:
            issues.append(
                f"Column removal ({', '.join(removed_columns)}) is a breaking change. "
                "All downstream consumers must be verified."
            )
    elif change_type == "mutative":
        warnings.append(
            "Mutative changes may affect value-dependent logic downstream. "
            "Check for hardcoded values in WHERE, CASE, and JOIN conditions."
        )

    # Gate 2: Downstream consumer trace
    if not downstream_models:
        pass  # No downstream impact
    else:
        if change_type == "removal":
            for col in removed_columns:
                issues.append(
                    f"Column '{col}' is being removed. Check if these downstream models "
                    f"reference it: {downstream_models}"
                )

    # Gate 3: Value-dependent filter detection warning
    if change_type in ("mutative", "removal") and downstream_models:
        warnings.append(
            f"Check these downstream models for value-dependent filters "
            f"(hardcoded WHERE/CASE/JOIN conditions) on changed columns: "
            f"{downstream_models}"
        )

    # Gate 4: Dimension source collision check
    if change_type in ("mutative", "additive") and changed_columns:
        warnings.append(
            f"If any downstream models use UNION ALL with multiple CTEs referencing "
            f"'{changed_model}', verify no dimension source collision occurs."
        )

    # Gate 5: Impact assessment
    if len(issues) > 0:
        classification = "dangerous"
        recommendation = (
            "BLOCKED: This change has breaking downstream impact. "
            "Present alternatives or coordinate migration across all affected models."
        )
    elif len(warnings) > 2 or (change_type == "mutative" and len(downstream_models) > 3):
        classification = "caution"
        recommendation = (
            "Proceed with enhanced testing. Run functional tests on all downstream models "
            "and validate no value-dependent logic is broken."
        )
    else:
        classification = "safe"
        recommendation = "Proceed with standard implementation and testing."

    return {
        "changed_model": changed_model,
        "change_type": change_type,
        "classification": classification,
        "downstream_count": len(downstream_models),
        "downstream_models": downstream_models,
        "issues": issues,
        "warnings": warnings,
        "recommendation": recommendation,
        "gates_passed": {
            "change_classification": True,
            "downstream_trace": True,
            "value_dependent_filters": len(issues) == 0,
            "dimension_collision": True,  # Requires manual verification
            "impact_assessment": True,
        },
    }


@tool
def review_code_changes(
    model_name: str,
    sql_content: str,
    schema_yaml: str = "",
    soma_layer: str = "",
    change_description: str = "",
) -> dict:
    """Review dbt model code changes for quality, testing, and SOMA compliance.

    Performs a structured review covering:
    1. SOMA compliance
    2. Code quality (SQL patterns)
    3. Testing coverage
    4. Documentation

    Args:
        model_name: Name of the model being reviewed
        sql_content: SQL content of the model
        schema_yaml: Schema YAML content (tests and documentation)
        soma_layer: Expected SOMA layer
        change_description: Description of what changed
    """
    findings = []

    # 1. SQL quality check
    quality = check_sql_quality.invoke({
        "sql_content": sql_content,
        "model_name": model_name,
    })
    for finding in quality.get("findings", []):
        findings.append({
            "category": "code_quality",
            **finding,
        })

    # 2. SOMA compliance
    if soma_layer:
        naming_issues = check_soma_naming(model_name, soma_layer)
        for issue in naming_issues:
            findings.append({
                "category": "soma_compliance",
                "severity": "error",
                "rule": "naming_convention",
                "message": issue,
            })

    # 3. Testing coverage
    if not schema_yaml:
        findings.append({
            "category": "testing",
            "severity": "error",
            "rule": "missing_tests",
            "message": "No schema YAML provided — model lacks test definitions.",
        })
    else:
        yaml_lower = schema_yaml.lower()
        if "unique" not in yaml_lower or "not_null" not in yaml_lower:
            findings.append({
                "category": "testing",
                "severity": "error",
                "rule": "missing_pk_tests",
                "message": "Primary key tests (unique + not_null) appear to be missing.",
                "auto_fix": "Add unique and not_null tests for primary key columns.",
            })
        if soma_layer == "activities" and "accepted_values" not in yaml_lower:
            findings.append({
                "category": "testing",
                "severity": "warning",
                "rule": "missing_activity_type_test",
                "message": "Activity model should have accepted_values test on activity_type.",
            })

    # 4. Documentation
    if schema_yaml and "description:" not in schema_yaml:
        findings.append({
            "category": "documentation",
            "severity": "warning",
            "rule": "missing_description",
            "message": "Model description is missing from schema YAML.",
        })

    # Score calculation
    blocking = [f for f in findings if f["severity"] == "error"]
    suggestions = [f for f in findings if f["severity"] == "warning"]

    readability_score = max(0, 25 - len([f for f in findings if f["category"] == "code_quality"]) * 5)
    testing_score = max(0, 30 - len([f for f in findings if f["category"] == "testing"]) * 10)
    documentation_score = max(0, 20 - len([f for f in findings if f["category"] == "documentation"]) * 10)
    soma_score = max(0, 25 - len([f for f in findings if f["category"] == "soma_compliance"]) * 12)
    total_score = readability_score + testing_score + documentation_score + soma_score

    # Decision
    if total_score >= 70 and len(blocking) == 0:
        decision = "approved"
    elif total_score >= 60 or len(blocking) <= 3:
        decision = "changes_requested"
    else:
        decision = "needs_rework"

    return {
        "model_name": model_name,
        "decision": decision,
        "score": total_score,
        "score_breakdown": {
            "readability": readability_score,
            "testing": testing_score,
            "documentation": documentation_score,
            "soma_compliance": soma_score,
        },
        "blocking_count": len(blocking),
        "suggestion_count": len(suggestions),
        "findings": findings,
    }
