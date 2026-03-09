"""
SOMA methodology tools for LangGraph agents.

Implements the SOMA decision tree, layer classification,
metric definition, and compliance validation as callable tools.
"""

from langchain_core.tools import tool


SOMA_DECISION_TREE = """
SOMA Layer Classification Decision Tree:

1. Is it an EVENT that occurs at a specific point in time?
   - Is it immutable (never updated after creation)? → ACTIVITY
   - Is it mutable (can be updated)? → ENTITY (track state changes as activities)

2. Is it a THING with attributes that change over time? → ENTITY

3. Is it a pre-computed metric or time-series aggregation? → NET

4. Is it raw data needing cleaning/renaming? → STAGING

Quick Classification Tests:
- Timestamp test: occurred_at → Activity, valid_from/to → Entity, period_start/end → Net
- Mutation test: APPEND only → Activity, UPDATE → Entity, RECALCULATE → Net
- Grain test: event occurrence → Activity, instance of thing → Entity, time period aggregation → Net
- PK test: entity_id+occurred_at → Activity, entity_id → Entity, entity_id+period_start → Net

Allowed Dependencies:
- Staging → Sources only
- Activities → Staging only
- Entities → Staging, Activities
- Nets → Activities, Entities
- NEVER: Entities→Nets, Activities→Entities, circular references
"""

SOMA_NAMING_CONVENTIONS = {
    "staging": "stg_{source}__{entity}",
    "activities": "act_{event_name}",
    "entities_fact": "fct_{entity}",
    "entities_dimension": "dim_{entity}",
    "nets": "net_{metric_domain}",
    "bridge": "bridge_{relationship}",
}

SOMA_REQUIRED_COLUMNS = {
    "activities": {
        "required": ["activity_id", "activity_type", "occurred_at"],
        "recommended": ["actor_id", "object_id", "recorded_at", "source_system"],
    },
    "entities": {
        "required": ["entity_sk or entity_id (PK)"],
        "recommended": ["_dbt_loaded_at", "source_system"],
    },
    "nets": {
        "required": ["grain columns", "metric columns", "measured_at", "valid_from", "valid_to"],
        "recommended": ["source_system"],
    },
}

INCREMENTAL_STRATEGY_BY_LAYER = {
    "activities": "append",
    "entities": "merge",
    "nets": "delete+insert",
}

SOMA_PREFIX_MAP = {
    "staging": ("stg_",),
    "activities": ("act_",),
    "entities": ("fct_", "dim_", "bridge_"),
    "nets": ("net_",),
}


def check_soma_naming(model_name: str, layer: str) -> list[str]:
    """Check if model_name follows the naming convention for the given SOMA layer.

    Returns a list of issues (empty if valid).
    """
    prefixes = SOMA_PREFIX_MAP.get(layer)
    if prefixes and not any(model_name.startswith(p) for p in prefixes):
        expected = ", ".join(prefixes)
        return [f"{layer} model should start with one of: {expected}. Got: {model_name}"]
    return []


@tool
def classify_soma_layer(
    model_description: str,
    has_occurred_at: bool = False,
    has_valid_from_to: bool = False,
    has_period_columns: bool = False,
    is_immutable: bool = False,
    is_raw_source: bool = False,
    has_metric_columns: bool = False,
) -> dict:
    """Classify a data model into the correct SOMA layer.

    Uses the SOMA decision tree to determine whether a model belongs
    in staging, activities, entities, or nets.

    Args:
        model_description: Description of what the model represents
        has_occurred_at: Model has an occurred_at timestamp (event time)
        has_valid_from_to: Model has valid_from/valid_to (SCD-style)
        has_period_columns: Model has period_start/period_end (aggregation)
        is_immutable: Data is never updated after creation
        is_raw_source: Data comes directly from a source system
        has_metric_columns: Model contains pre-computed metric values
    """
    if is_raw_source:
        layer = "staging"
        naming = SOMA_NAMING_CONVENTIONS["staging"]
        strategy = "view"
        reasoning = "Raw source data should be cleaned and renamed in staging."
    elif has_period_columns or (has_metric_columns and not has_occurred_at):
        layer = "nets"
        naming = SOMA_NAMING_CONVENTIONS["nets"]
        strategy = INCREMENTAL_STRATEGY_BY_LAYER["nets"]
        reasoning = (
            "Pre-computed metrics or time-series aggregations belong in nets. "
            "Nets use bi-temporal columns (valid_from, valid_to) and delete+insert strategy."
        )
    elif has_occurred_at and is_immutable:
        layer = "activities"
        naming = SOMA_NAMING_CONVENTIONS["activities"]
        strategy = INCREMENTAL_STRATEGY_BY_LAYER["activities"]
        reasoning = (
            "Immutable events with occurred_at are activities. "
            "Activities use append-only incremental strategy."
        )
    elif has_valid_from_to or (has_occurred_at and not is_immutable):
        layer = "entities"
        naming = SOMA_NAMING_CONVENTIONS["entities_fact"]
        strategy = INCREMENTAL_STRATEGY_BY_LAYER["entities"]
        reasoning = (
            "Mutable records or things with changing attributes are entities. "
            "Entities use merge incremental strategy."
        )
    else:
        layer = "entities"
        naming = SOMA_NAMING_CONVENTIONS["entities_fact"]
        strategy = INCREMENTAL_STRATEGY_BY_LAYER["entities"]
        reasoning = (
            "Default classification is entity. If this represents an event, "
            "reconsider as activity. Provide more context for accurate classification."
        )

    return {
        "layer": layer,
        "naming_convention": naming,
        "incremental_strategy": strategy,
        "required_columns": SOMA_REQUIRED_COLUMNS.get(layer, {}),
        "reasoning": reasoning,
        "decision_tree": SOMA_DECISION_TREE,
    }


@tool
def validate_soma_compliance(
    model_name: str,
    layer: str,
    columns: list[str],
    dependencies: list[str],
    materialization: str = "",
    incremental_strategy: str = "",
) -> dict:
    """Validate that a model follows SOMA conventions.

    Checks naming, required columns, dependency rules, and materialization.

    Args:
        model_name: Name of the dbt model
        layer: SOMA layer (staging, activities, entities, nets)
        columns: List of column names in the model
        dependencies: List of model names this model depends on (ref/source)
        materialization: dbt materialization type
        incremental_strategy: Incremental strategy if applicable
    """
    issues = []
    warnings = []

    # Naming convention check
    issues.extend(check_soma_naming(model_name, layer))

    # Required columns check
    required = SOMA_REQUIRED_COLUMNS.get(layer, {}).get("required", [])
    columns_lower = [c.lower() for c in columns]
    if layer == "activities":
        for col in ["activity_id", "activity_type", "occurred_at"]:
            if col not in columns_lower:
                issues.append(f"Activity model missing required column: {col}")
    elif layer == "nets":
        for col in ["measured_at", "valid_from", "valid_to"]:
            if col not in columns_lower:
                issues.append(f"Net model missing required column: {col}")

    # Dependency rules check
    allowed_deps = {
        "staging": ["source"],
        "activities": ["stg_"],
        "entities": ["stg_", "act_", "fct_", "dim_"],
        "nets": ["act_", "fct_", "dim_", "net_"],
    }
    allowed_prefixes = allowed_deps.get(layer, [])
    for dep in dependencies:
        if dep.startswith("source."):
            if layer != "staging":
                warnings.append(f"Direct source reference in {layer} layer: {dep}. Consider staging first.")
        elif not any(dep.startswith(p) for p in allowed_prefixes):
            issues.append(
                f"Invalid dependency for {layer} layer: {dep}. "
                f"Allowed prefixes: {allowed_prefixes}"
            )

    # Incremental strategy check
    expected_strategy = INCREMENTAL_STRATEGY_BY_LAYER.get(layer)
    if expected_strategy and incremental_strategy and incremental_strategy != expected_strategy:
        warnings.append(
            f"Expected incremental strategy '{expected_strategy}' for {layer}, "
            f"got '{incremental_strategy}'."
        )

    compliant = len(issues) == 0
    return {
        "compliant": compliant,
        "issues": issues,
        "warnings": warnings,
        "layer": layer,
        "model_name": model_name,
        "expected_naming": SOMA_PREFIX_MAP.get(layer, ()),
        "expected_strategy": expected_strategy,
    }


@tool
def define_metric(
    name: str,
    label: str,
    metric_type: str,
    calculation_type: str,
    description: str,
    business_definition: str,
    formula: str = "",
    filters: list[dict] | None = None,
    dimensions: list[str] | None = None,
    components: list[str] | None = None,
    owner: str = "",
    time_grains: list[str] | None = None,
) -> dict:
    """Create a SOMA-compliant metric definition.

    Validates the metric follows SOMA patterns and returns a complete
    metric specification ready for implementation.

    Args:
        name: Metric name (snake_case)
        label: Human-readable label
        metric_type: 'atomic' or 'compound'
        calculation_type: count, count_distinct, sum, average, ratio, min, max
        description: Technical description
        business_definition: Plain-language business definition
        formula: Formula for compound metrics (e.g., '${revenue} / nullif(${customer_count}, 0)')
        filters: List of filter dicts with 'field' and 'value' keys
        dimensions: Available dimension columns for slicing
        components: Component metric names for compound metrics
        owner: Team or person owning this metric
        time_grains: Supported time grains (day, week, month, quarter, year)
    """
    filters = filters or []
    dimensions = dimensions or []
    components = components or []
    time_grains = time_grains or []
    issues = []

    # Validate metric type
    if metric_type not in ("atomic", "compound"):
        issues.append(f"metric_type must be 'atomic' or 'compound', got '{metric_type}'")

    # Compound metric validation
    if metric_type == "compound":
        if not formula:
            issues.append("Compound metrics require a formula")
        if not components:
            issues.append("Compound metrics require component metric references")
        if "nullif" not in formula.lower() and "/" in formula:
            issues.append("Division in formula should use NULLIF for safe division")
    else:
        if formula:
            issues.append("Atomic metrics should not have a formula (use calculation_type instead)")

    # Naming validation
    if not name.replace("_", "").isalnum():
        issues.append("Metric name should be snake_case alphanumeric")

    # Required fields
    if not business_definition:
        issues.append("business_definition is required for all metrics")
    if not time_grains:
        issues.append("At least one time_grain should be specified")

    valid = len(issues) == 0
    spec = {
        "name": name,
        "label": label,
        "type": metric_type,
        "calculation_type": calculation_type,
        "description": description,
        "business_definition": business_definition,
        "owner": owner,
        "time_grains": time_grains or ["day", "week", "month", "quarter", "year"],
        "dimensions": dimensions,
        "filters": filters,
    }
    if metric_type == "compound":
        spec["formula"] = formula
        spec["components"] = components

    return {
        "valid": valid,
        "issues": issues,
        "spec": spec,
    }


@tool
def validate_metric(
    metric_name: str,
    expected_value: float,
    actual_value: float,
    time_period: str,
    source_description: str = "",
) -> dict:
    """Validate a metric calculation by comparing expected vs actual values.

    Identifies variance and suggests investigation paths based on
    the discrepancy pattern.

    Args:
        metric_name: Name of the metric being validated
        expected_value: Expected/source-of-truth value
        actual_value: Calculated/reported value
        time_period: Time period being validated (e.g., '2024-01')
        source_description: Description of the expected value source
    """
    if expected_value == 0:
        variance_pct = 100.0 if actual_value != 0 else 0.0
    else:
        variance_pct = abs((actual_value - expected_value) / expected_value) * 100

    difference = actual_value - expected_value

    # Determine investigation path based on pattern
    if variance_pct == 0:
        status = "match"
        investigation = "Values match. No investigation needed."
    elif variance_pct < 1:
        status = "minor_variance"
        investigation = (
            "Minor variance (<1%). Check rounding differences, "
            "timezone handling, or filter edge cases."
        )
    elif variance_pct < 5:
        status = "moderate_variance"
        investigation = (
            "Moderate variance (1-5%). Check: date range boundaries, "
            "filter differences, aggregation level mismatches, "
            "or data freshness/timing differences."
        )
    elif abs(difference) == int(difference) and difference > 0:
        status = "exact_offset"
        investigation = (
            f"Exact offset of {difference}. Likely caused by: "
            "missing/extra filter condition, duplicate records, "
            "or inclusion/exclusion of specific records."
        )
    elif round(variance_pct) in (50, 100, 200):
        status = "multiplier_variance"
        investigation = (
            f"Variance is ~{round(variance_pct)}% — suggests a multiplier issue. "
            "Check: double-counting from fan-out joins, "
            "missing DISTINCT, or aggregation grain mismatch."
        )
    else:
        status = "significant_variance"
        investigation = (
            f"Significant variance ({variance_pct:.1f}%). Systematic investigation needed: "
            "1) Confirm definitions match, 2) Trace from source to reporting, "
            "3) Check each transformation layer, 4) Compare filters and date logic."
        )

    return {
        "metric_name": metric_name,
        "time_period": time_period,
        "expected_value": expected_value,
        "actual_value": actual_value,
        "difference": difference,
        "variance_pct": round(variance_pct, 2),
        "status": status,
        "investigation": investigation,
        "passed": variance_pct < 1,
    }


@tool
def check_metric_uniqueness(
    metric_name: str,
    existing_metrics: list[str],
) -> dict:
    """Check if a metric name is unique and doesn't duplicate existing metrics.

    Args:
        metric_name: Proposed metric name
        existing_metrics: List of existing metric names to check against
    """
    exact_match = metric_name in existing_metrics

    # Check for similar names (fuzzy)
    similar = []
    name_parts = set(metric_name.split("_"))
    for existing in existing_metrics:
        existing_parts = set(existing.split("_"))
        overlap = name_parts & existing_parts
        if len(overlap) >= 2 and existing != metric_name:
            similar.append(existing)

    return {
        "is_unique": not exact_match,
        "exact_match": exact_match,
        "similar_metrics": similar,
        "recommendation": (
            "Name is unique." if not exact_match and not similar
            else f"Exact duplicate found: {metric_name}" if exact_match
            else f"Similar metrics exist: {similar}. Verify this is not a duplicate."
        ),
    }
