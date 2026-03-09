# Test Patterns by Model Type

Comprehensive guide to required tests for each SOMA model type.

## Model Type Overview

| Model Type | Primary Focus | Minimum Tests | Typical Count |
|------------|--------------|---------------|---------------|
| Staging (`stg_*`) | Source data quality | 2 | 3-4 |
| Activity (`act_*`) | Event integrity | 3 | 4-5 |
| Fact (`fct_*`) | Referential integrity | 4 | 5-6 |
| Dimension (`dim_*`) | Business rules | 3 | 4-5 |
| Net (`net_*`) | Metric accuracy | 5 | 6-8 |

---

## Staging Models (`stg_*`)

### Purpose
Clean and standardize raw source data before transformations.

### Required Tests

```yaml
models:
  - name: stg_source__entity
    columns:
      - name: entity_id  # Natural key from source
        tests:
          - unique
          - not_null

      - name: _loaded_at  # Metadata timestamp
        tests:
          - not_null

      - name: status  # If categorical
        tests:
          - accepted_values:
              values: ['active', 'inactive', 'pending']
```

### Test Checklist
- [ ] Natural primary key: `unique` + `not_null`
- [ ] Timestamp column: `not_null`
- [ ] Categorical columns: `accepted_values`
- [ ] Critical columns: `not_null`

### Source Freshness

```yaml
sources:
  - name: salesforce
    freshness:
      warn_after: {count: 24, period: hour}
      error_after: {count: 48, period: hour}
    tables:
      - name: accounts
        loaded_at_field: _fivetran_synced
```

---

## Activity Models (`act_*`)

### Purpose
Immutable event streams capturing business activities.

### Required Tests

```yaml
models:
  - name: act_contract_events
    columns:
      - name: activity_id  # Surrogate key
        tests:
          - unique
          - not_null

      - name: occurred_at  # Event timestamp
        tests:
          - not_null
          - dbt_utils.expression_is_true:
              expression: "<= current_timestamp()"

      - name: activity_type  # Event classification
        tests:
          - not_null
          - accepted_values:
              values: ['contract_won', 'contract_lost', 'contract_renewed']

      - name: contract_id  # FK to entity
        tests:
          - not_null
          - relationships:
              to: ref('dim_contracts')
              field: contract_id
```

### Test Checklist
- [ ] `activity_id`: `unique` + `not_null`
- [ ] `occurred_at`: `not_null` + timestamp validity
- [ ] `activity_type`: `not_null` + `accepted_values`
- [ ] Foreign keys: `relationships` tests
- [ ] Amount columns: non-negative checks

### Activity-Specific Patterns

**Timestamp Validity:**
```yaml
- name: occurred_at
  tests:
    - dbt_utils.expression_is_true:
        expression: "between '2020-01-01' and current_date()"
        config:
          severity: warn
```

**Activity Type Exhaustiveness:**
```yaml
- name: activity_type
  tests:
    - accepted_values:
        values: ['won', 'lost', 'renewed', 'expanded']
        config:
          severity: error
```

---

## Fact Models (`fct_*`)

### Purpose
Transactional or snapshot facts with foreign keys to dimensions.

### Required Tests

```yaml
models:
  - name: fct_orders
    columns:
      - name: order_id  # Primary key
        tests:
          - unique
          - not_null

      - name: customer_id  # FK
        tests:
          - not_null
          - relationships:
              to: ref('dim_customers')
              field: customer_id

      - name: product_id  # FK
        tests:
          - not_null
          - relationships:
              to: ref('dim_products')
              field: product_id

      - name: order_amount  # Measure
        tests:
          - not_null
          - dbt_utils.expression_is_true:
              expression: ">= 0"

      - name: order_date
        tests:
          - not_null
          - dbt_utils.expression_is_true:
              expression: "<= current_date()"
```

### Test Checklist
- [ ] Primary key: `unique` + `not_null`
- [ ] All foreign keys: `relationships` tests
- [ ] Amount columns: non-negative validation
- [ ] Date columns: reasonable range checks
- [ ] Business rule validations

### Fact-Specific Patterns

**Multi-Column Business Rules:**
```yaml
tests:
  # Ship date must be >= order date
  - dbt_utils.expression_is_true:
      expression: "shipped_date >= order_date OR shipped_date IS NULL"

  # Discount cannot exceed total
  - dbt_utils.expression_is_true:
      expression: "discount_amount <= total_amount"
```

**Conditional Requirements:**
```yaml
tests:
  # Amount required when status is 'paid'
  - dbt_utils.expression_is_true:
      expression: "NOT (status = 'paid' AND amount IS NULL)"
```

---

## Dimension Models (`dim_*`)

### Purpose
Descriptive attributes for analysis, often denormalized.

### Required Tests

```yaml
models:
  - name: dim_customers
    columns:
      - name: customer_id  # Surrogate or natural key
        tests:
          - unique
          - not_null

      - name: customer_name
        tests:
          - not_null

      - name: customer_segment  # Business classification
        tests:
          - accepted_values:
              values: ['Enterprise', 'Mid-Market', 'SMB', 'Consumer']

      - name: status
        tests:
          - not_null
          - accepted_values:
              values: ['active', 'inactive', 'suspended']

      - name: is_active  # Boolean flag
        tests:
          - not_null
          - accepted_values:
              values: [true, false]
```

### Test Checklist
- [ ] Primary key: `unique` + `not_null`
- [ ] Name/description: `not_null`
- [ ] Status/type columns: `accepted_values`
- [ ] Boolean flags: `accepted_values` [true, false]
- [ ] Email/phone: format validation (if applicable)

### Dimension-Specific Patterns

**SCD Type 2 (Slowly Changing Dimensions):**
```yaml
models:
  - name: dim_customers_scd
    columns:
      - name: customer_key  # Surrogate key (version-specific)
        tests:
          - unique
          - not_null

      - name: customer_id  # Natural key (not unique in SCD2)
        tests:
          - not_null

      - name: valid_from
        tests:
          - not_null

      - name: valid_to
        tests:
          - not_null

      - name: is_current
        tests:
          - not_null
          - accepted_values:
              values: [true, false]

    tests:
      # Only one current record per natural key
      - dbt_utils.unique_combination_of_columns:
          combination_of_columns:
            - customer_id
            - is_current
          where: "is_current = true"

      # Valid date range
      - dbt_utils.expression_is_true:
          expression: "valid_from < valid_to OR valid_to = '9999-12-31'"
```

**Reference Data Dimensions:**
```yaml
# For small lookup tables
tests:
  - dbt_expectations.expect_table_row_count_to_be_between:
      min_value: 10
      max_value: 100
      config:
        severity: warn
```

---

## Net Models (`net_*`)

### Purpose
Bi-temporal reporting tables optimized for Power BI/BI tools.

### Required Tests

```yaml
models:
  - name: net_revenue_metrics
    columns:
      # Time dimensions
      - name: date_month
        tests:
          - not_null

      - name: measured_at  # When metric was calculated
        tests:
          - not_null

      - name: valid_from  # Bi-temporal
        tests:
          - not_null

      - name: valid_to  # Bi-temporal
        tests:
          - not_null

      # Metrics should allow nulls (0 vs null distinction)
      - name: revenue
        tests:
          - dbt_utils.expression_is_true:
              expression: ">= 0 OR revenue IS NULL"

    tests:
      # Composite grain uniqueness
      - dbt_utils.unique_combination_of_columns:
          combination_of_columns:
            - date_month
            - customer_segment
            - product_tier
            - measured_at

      # Bi-temporal validity
      - dbt_utils.expression_is_true:
          expression: "valid_from <= valid_to"

      # measured_at in valid range
      - dbt_utils.expression_is_true:
          expression: "measured_at between valid_from and valid_to"
```

### Test Checklist
- [ ] Grain columns: composite uniqueness
- [ ] `measured_at`: `not_null`
- [ ] `valid_from` & `valid_to`: `not_null`
- [ ] Bi-temporal: `valid_from <= valid_to`
- [ ] Metric formulas: consistency validation
- [ ] Negative amounts: check if allowed

### Net-Specific Patterns

**Metric Formula Consistency:**
```sql
-- tests/assert_revenue_components_sum.sql
SELECT *
FROM {{ ref('net_revenue_metrics') }}
WHERE ABS(
    total_revenue - (new_revenue + recurring_revenue + expansion_revenue)
) > 0.01
  AND total_revenue IS NOT NULL;
```

**Compound Metric Validation:**
```sql
-- tests/assert_cac_formula.sql
SELECT *
FROM {{ ref('net_acquisition_metrics') }}
WHERE ABS(
    cac - (sales_marketing_spend / NULLIF(new_customers, 0))
) > 0.01
  AND new_customers > 0;
```

**No Future Dates in Historical Data:**
```yaml
tests:
  - dbt_utils.expression_is_true:
      expression: "date_month <= date_trunc('month', current_date())"
      config:
        severity: error
```

---

## Common Test Patterns (All Types)

### Primary Key Pattern

```yaml
- name: id_column
  tests:
    - unique
    - not_null
```

### Foreign Key Pattern

```yaml
- name: foreign_id
  tests:
    - not_null
    - relationships:
        to: ref('parent_table')
        field: parent_id
        config:
          severity: error
```

### Categorical Field Pattern

```yaml
- name: status_column
  tests:
    - accepted_values:
        values: ['value1', 'value2', 'value3']
        config:
          severity: warn  # Or error if critical
```

### Numeric Range Pattern

```yaml
- name: amount
  tests:
    - not_null
    - dbt_utils.expression_is_true:
        expression: ">= 0"  # Non-negative

- name: percentage
  tests:
    - dbt_utils.expression_is_true:
        expression: "between 0 and 100"
```

### Date Validity Pattern

```yaml
- name: event_date
  tests:
    - not_null
    - dbt_utils.expression_is_true:
        expression: "between '2020-01-01' and current_date()"
        config:
          severity: warn
```

### Boolean Pattern

```yaml
- name: is_active
  tests:
    - not_null
    - accepted_values:
        values: [true, false]
```

---

## Testing Strategy Summary

| Layer | Focus | Key Tests |
|-------|-------|-----------|
| **Staging** | Source quality | PK unique/not_null, freshness |
| **Activities** | Event integrity | activity_id, occurred_at, activity_type |
| **Entities** | Referential integrity | PK, FKs, business rules |
| **Nets** | Metric accuracy | Composite grain, bi-temporal, formulas |

---

## Quick Reference Table

| Column Type | Required Tests |
|-------------|----------------|
| Primary Key | `unique`, `not_null` |
| Foreign Key | `not_null`, `relationships` |
| Status/Type | `accepted_values` |
| Amount | `not_null`, `>= 0` (usually) |
| Percentage | `between 0 and 100` |
| Date | `not_null`, reasonable range |
| Boolean | `accepted_values: [true, false]` |
| Bi-temporal | `not_null`, `valid_from <= valid_to` |
| Natural Key (staging) | `unique`, `not_null` |
| Surrogate Key (SCD) | `unique`, `not_null` |
