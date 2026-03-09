---
name: dbt-testing
description: dbt testing best practices and patterns. Use when: "add tests", "write tests", "schema.yml", "test coverage", "what tests do I need", "test this model", "required tests", "unique test", "not_null test", "relationships test", "data quality test", "test patterns"
---

# dbt Testing Guide

Quick reference for dbt schema testing standards in this project.

## Schema Tests vs Unit Tests

**Schema Tests** (this skill):
- ✅ Testing data values (unique, not_null, accepted_values)
- ✅ Validating relationships between tables (foreign keys)
- ✅ Checking business rules on actual warehouse data
- ✅ SOMA-specific tests (activity grain, entity relationships)

**Unit Tests** ([dbt-labs skill](../dbt-labs/skills/adding-dbt-unit-test/)):
- ✅ Testing complex SQL logic with mocked data
- ✅ TDD workflow (write tests before implementing SQL)
- ✅ Testing edge cases without materializing full datasets

**Use both for comprehensive coverage**: Unit tests for logic validation, schema tests for data quality validation.

---

## Quick Reference: Must-Have Tests

| Column Type | Required Tests |
|-------------|----------------|
| Primary Key | `unique`, `not_null` |
| Foreign Key | `not_null`, `relationships` |
| Status/Type | `accepted_values` |
| Amount | `not_null`, `>= 0` |
| Percentage | `between 0 and 100` |
| Date | `not_null`, reasonable range |
| Boolean | `accepted_values: [true, false]` |
| Bi-temporal | `not_null`, `valid_from <= valid_to` |

---

## Required Tests by SOMA Model Type

| Model Type | Minimum Tests | Details |
|------------|---------------|---------|
| **Staging** (`stg_*`) | PK: `unique` + `not_null`<br>Timestamp: `not_null` | [See patterns →](references/test-patterns-by-type.md#staging-models) |
| **Activity** (`act_*`) | `activity_id`: `unique` + `not_null`<br>`occurred_at`: `not_null`<br>`activity_type`: `accepted_values` | [See patterns →](references/test-patterns-by-type.md#activity-models) |
| **Fact** (`fct_*`) | PK: `unique` + `not_null`<br>FKs: `relationships`<br>Amounts: `>= 0` | [See patterns →](references/test-patterns-by-type.md#fact-models) |
| **Dimension** (`dim_*`) | PK: `unique` + `not_null`<br>Status: `accepted_values`<br>Booleans: `[true, false]` | [See patterns →](references/test-patterns-by-type.md#dimension-models) |
| **Net** (`net_*`) | Composite uniqueness<br>Bi-temporal validity<br>Metric formulas | [See patterns →](references/test-patterns-by-type.md#net-models) |

**Detailed patterns and YAML examples**: See [references/test-patterns-by-type.md](references/test-patterns-by-type.md)

---

## Common Test Patterns

### Primary Key
```yaml
- name: order_id
  tests:
    - unique
    - not_null
```

### Foreign Key
```yaml
- name: customer_id
  tests:
    - not_null
    - relationships:
        to: ref('dim_customers')
        field: customer_id
```

### Categorical Field
```yaml
- name: order_status
  tests:
    - accepted_values:
        values: ['pending', 'paid', 'shipped', 'cancelled']
```

### Numeric Range
```yaml
- name: amount
  tests:
    - not_null
    - dbt_utils.expression_is_true:
        expression: ">= 0"
```

### Composite Uniqueness (Nets)
```yaml
tests:
  - dbt_utils.unique_combination_of_columns:
      combination_of_columns:
        - date_month
        - dimension_1
        - dimension_2
```

**More patterns and business rule tests**: See [references/test-patterns-by-type.md](references/test-patterns-by-type.md)

---

## Running Tests

### Command Line
```bash
# Run all tests
dbt test

# Run tests for specific model
dbt test --select fct_orders

# Run with failure storage
dbt test --store-failures

# Run and inspect failures
dbt test --select fct_orders --store-failures
# Then: select * from dbt_test_failures.unique_fct_orders_order_id
```

### MCP Tools
| Task | MCP Tool | Example |
|------|----------|---------|
| Run model tests | `mcp__dbt__test` | `selector: "fct_orders"` |
| Run model + tests | `mcp__dbt__build` | `selector: "fct_orders"` |
| Check test results | `mcp__snowflake__run_snowflake_query` | Query dbt_test_failures table |

**Detailed inspection queries**: See [scripts/inspect-test-failures.sql](scripts/inspect-test-failures.sql)

---

## Test Failure Troubleshooting

### Quick Diagnosis Steps
1. **Run with failure storage**: `dbt test --select model_name --store-failures`
2. **Inspect failures**: Query `dbt_test_failures.{test_name}` table
3. **Identify pattern**: Use [scripts/inspect-test-failures.sql](scripts/inspect-test-failures.sql)
4. **Apply fix**: See common fixes below
5. **Re-run**: `dbt test --select model_name`

### Common Failure Causes & Fixes

| Test Type | Common Cause | Quick Fix |
|-----------|--------------|-----------|
| `unique` | Duplicate source records | Add `QUALIFY ROW_NUMBER() OVER (...) = 1` |
| `not_null` | Missing data in source | Add `COALESCE(col, 'Unknown')` or filter |
| `relationships` | Orphan foreign keys | Use `INNER JOIN` or filter orphans |
| `accepted_values` | New category in source | Update accepted values list |
| `expression_is_true` | Business rule violation | Fix calculation or add exception logic |

**Detailed troubleshooting guide**: See [references/test-failure-diagnosis.md](references/test-failure-diagnosis.md)

---

## Test Coverage Check

### Run Coverage Analysis
```bash
# Check coverage for all models
bash scripts/test-coverage-check.sh

# Target coverage by model type
# Staging:   2+ tests
# Activity:  3+ tests
# Fact:      4+ tests
# Dimension: 3+ tests
# Net:       5+ tests
```

**Coverage script**: [scripts/test-coverage-check.sh](scripts/test-coverage-check.sh)

---

## Test Checklist

Before merging any model:

- [ ] Primary key has `unique` + `not_null`
- [ ] Foreign keys have `relationships` test
- [ ] Status/type columns have `accepted_values`
- [ ] Amount columns have range validation
- [ ] Date columns have validity checks
- [ ] Boolean columns have `accepted_values` [true, false]
- [ ] Nets have composite uniqueness test
- [ ] Nets have bi-temporal validity test
- [ ] Custom tests for business rules (if applicable)
- [ ] All tests pass locally: `dbt test --select model_name`

---

## Useful dbt_utils Tests

```yaml
# Expression evaluation
- dbt_utils.expression_is_true:
    expression: "column > 0"

# Unique combination
- dbt_utils.unique_combination_of_columns:
    combination_of_columns: [col1, col2]

# Recency check
- dbt_utils.recency:
    datepart: day
    field: updated_at
    interval: 1

# At least one not null
- dbt_utils.at_least_one:
    column_name: important_field
```

---

## Test Configuration

### Severity Levels
```yaml
tests:
  - not_null:
      config:
        severity: error  # Fail the build
  - accepted_values:
      values: [...]
      config:
        severity: warn  # Warning only
```

**Guidelines:**
- `error`: Data integrity issues (duplicates, null PKs)
- `warn`: Data quality issues (unexpected values, anomalies)

### Store Failures
```yaml
tests:
  - unique:
      config:
        store_failures: true
        schema: dbt_test_failures
```

---

## Detailed Guides

For comprehensive testing patterns and troubleshooting:

- **[Test Patterns by Type](references/test-patterns-by-type.md)** - Required tests for staging, activity, fact, dimension, and net models with YAML examples
- **[Test Failure Diagnosis](references/test-failure-diagnosis.md)** - Systematic troubleshooting for each test type with diagnosis queries and fixes

## Scripts

- **[Test Coverage Check](scripts/test-coverage-check.sh)** - Analyze test coverage across all models
- **[Inspect Test Failures](scripts/inspect-test-failures.sql)** - SQL queries for investigating test failures in Snowflake

---

## Memory Integration

When troubleshooting test failures:
- **Check memory first**: `.claude/memory/patterns/common-test-failures.json`
- **Query**: "Have we seen this test failure pattern before?"
- **Reference past fixes**: Similar failures often have similar solutions

After fixing test failures:
- **Update patterns**: If new failure type, add to `common-test-failures.json`
- **Document fix**: Store episode in `.claude/memory/episodes/`
