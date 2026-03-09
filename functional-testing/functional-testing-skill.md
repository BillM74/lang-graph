---
name: functional-testing
description: Functional testing patterns for semantic data validation beyond schema tests. Use when: "check for duplicates", "duplicate detection", "YTD accumulation", "YTD is wrong", "cross-model consistency", "dimension collision", "dimension source collision", "validate accumulation", "semantic validation", "business logic test", "data means what it should", "post-implementation validation"
---

# Functional Testing Guide

Apply these patterns when validating data correctness **beyond** what `dbt test` catches. Schema tests check structure (unique, not_null, accepted_values). Functional tests check **semantic correctness** — that the data means what it should mean.

## Schema Tests vs Functional Tests

| Aspect | Schema Tests (`dbt test`) | Functional Tests (this skill) |
|--------|--------------------------|-------------------------------|
| Checks | Structure (unique, not_null, FK) | Meaning (correct values, consistent sources) |
| Catches | Duplicate PKs, missing data | Duplicate rows from dimension collisions, wrong aggregations |
| Runs | Automated in CI/CD | Ad-hoc via Snowflake queries after changes |
| Examples | `unique` on `order_id` | Branch totals match region rollups |

**Use both**: Schema tests for automated quality gates. Functional tests for semantic validation after implementation changes.

---

## Functional Test Patterns

### Pattern 1: Duplicate Detection (Dimension Value Collision)

**When to use:** After modifying models that join dimension attributes or UNION ALL multiple CTEs.

**What it catches:** Same entity appearing with multiple dimension values (e.g., a branch with both 'Corporate' and 'Back Office' regions).

```sql
-- Detect entities with multiple dimension values
SELECT
    entity_column,
    COUNT(DISTINCT dimension_column) as distinct_values,
    LISTAGG(DISTINCT dimension_column, ', ') as values_found
FROM {{ ref('model_name') }}
WHERE aggregation_level = 'Branch'  -- adjust filter as needed
GROUP BY 1
HAVING COUNT(DISTINCT dimension_column) > 1
ORDER BY distinct_values DESC;
```

**Real example from this project:**
```sql
-- Admin branches had two different regions from two different sources
SELECT branch_location, LISTAGG(DISTINCT region, ', ') as regions
FROM ANALYTICS.ATOMIC.revenue_metrics
WHERE aggregation_level = 'Branch'
GROUP BY branch_location
HAVING COUNT(DISTINCT region) > 1;
-- Found: BO, BRAdmin, CIRACON, REALINSURE, Real Manage LLC, Vendor Services
-- Each had both 'Corporate' (from dim_branches) and 'Back Office' (from reporting_gl_consolidated)
```

---

### Pattern 2: YTD Accumulation Verification

**When to use:** After adding or modifying window functions that compute YTD values.

**What it catches:** Incorrect PARTITION BY, wrong ORDER BY, missing ROWS clause.

```sql
-- Verify YTD = cumulative sum of period values
WITH verification AS (
    SELECT
        branch_location, region, metric_name, metric_section,
        aggregation_level, year_num, period_month,
        ytd_value,
        SUM(current_period_value) OVER (
            PARTITION BY branch_location, region, metric_name, metric_section,
                         aggregation_level, year_num
            ORDER BY period_month
            ROWS UNBOUNDED PRECEDING
        ) as expected_ytd
    FROM {{ ref('model_name') }}
    WHERE aggregation_level = 'Branch'
      AND ytd_value IS NOT NULL
)
SELECT *
FROM verification
WHERE ABS(COALESCE(ytd_value, 0) - COALESCE(expected_ytd, 0)) > 0.01
LIMIT 20;
```

**Key checks:**
- PARTITION BY must include all dimension columns that distinguish rows (e.g., `metric_section` not just `metric_name`)
- ORDER BY must be `period_month` (not period date or year)
- For ratios/percentages, YTD should be NULL (cumulative sum of percentages is mathematically wrong)

---

### Pattern 3: Cross-Model Consistency

**When to use:** After modifying atomic or composite models that feed into hierarchical aggregation.

**What it catches:** Branch-level rows that don't sum to region-level rows, or region-level rows that don't sum to company-level.

```sql
-- Branch totals should match Region totals
WITH branch_totals AS (
    SELECT region, metric_name, metric_section, period_month, year_num,
           SUM(current_period_value) as branch_sum
    FROM {{ ref('model_name') }}
    WHERE aggregation_level = 'Branch'
    GROUP BY 1, 2, 3, 4, 5
),
region_values AS (
    SELECT region, metric_name, metric_section, period_month, year_num,
           current_period_value as region_total
    FROM {{ ref('model_name') }}
    WHERE aggregation_level = 'Region'
)
SELECT
    COALESCE(b.region, r.region) as region,
    COALESCE(b.metric_name, r.metric_name) as metric_name,
    b.branch_sum,
    r.region_total,
    ABS(COALESCE(b.branch_sum, 0) - COALESCE(r.region_total, 0)) as variance
FROM branch_totals b
FULL OUTER JOIN region_values r
    USING (region, metric_name, metric_section, period_month, year_num)
WHERE ABS(COALESCE(b.branch_sum, 0) - COALESCE(r.region_total, 0)) > 0.01
ORDER BY variance DESC
LIMIT 20;
```

---

### Pattern 4: Dimension Source Consistency (Code-Level Audit)

**When to use:** When reviewing models that UNION ALL multiple CTEs, or during code review.

**What it catches:** CTEs that source the same dimension attribute from different models, creating silent duplicates.

**How to audit:**

1. For each UNION ALL model, list all CTEs and where they get each dimension column:

```
CTE Name        | region source           | Canonical?
revenue_base    | aa.region (from spine)  | Yes (dim_branches)
vendserv_base   | bb.region (from GL)     | NO - uses reporting_gl_consolidated
ins_base        | bb.region (from GL)     | NO - uses reporting_gl_consolidated
```

2. If any CTE gets a shared dimension from a different source, flag it.

**Fix pattern:**
```sql
-- BEFORE (dimension source collision):
vendserv_base AS (
    SELECT
        bb.branch_location,
        bb.region,  -- from reporting_gl_consolidated (WRONG SOURCE)
        ...
    FROM {{ ref("reporting_gl_consolidated") }} bb
)

-- AFTER (canonical dimension source):
vendserv_base AS (
    SELECT
        bb.branch_location,
        db.region,  -- canonical region from dim_branches
        ...
    FROM {{ ref("reporting_gl_consolidated") }} bb
    LEFT JOIN {{ ref("dim_branches") }} db ON bb.branch_location = db.branch_location
)
```

---

### Pattern 5: Edge Case Validation

**When to use:** After any model change. Admin/system entities often have special behavior.

**What it catches:** Admin branches, system accounts, and other edge cases that produce unexpected row multiplication or misclassification.

```sql
-- Check admin/system branches for anomalies
SELECT
    branch_location,
    COUNT(DISTINCT region) as distinct_regions,
    COUNT(DISTINCT metric_category) as distinct_categories,
    COUNT(*) as total_rows
FROM {{ ref('model_name') }}
WHERE aggregation_level = 'Branch'
  AND branch_location IN (
    -- Known admin branches in this project
    'BO', 'BRAdmin', 'CIRACON', 'REALINSURE', 'Real Manage LLC',
    'Vendor Services', 'Back Office'
  )
GROUP BY 1
ORDER BY distinct_regions DESC, total_rows DESC;
```

---

## Anti-Patterns

### Anti-Pattern 1: "Fix the Source" Without Impact Analysis

**Symptom:** Tracing a data issue to a seed/source and immediately changing the value.

**Why it's dangerous:** Source values may be intentionally different because downstream models use them as business logic filters.

**Real example:**
- `account_metadata.csv` had `region = 'Back Office'` for admin branches
- `dim_branches` normalized these to `region = 'Corporate'`
- Initial instinct: change `account_metadata` to 'Corporate'
- **Impact:** Would have zeroed out ALL Back Office Expenses because `backoffice_expenses_metrics.sql` filters `bb.region = 'Back Office'` and `branch_infrastructure_metrics.sql` / `onsite_expenses_metrics.sql` filter `bb.region <> 'Back Office'`
- **Correct fix:** Change the consumer (`revenue_metrics.sql`) to use the canonical source, not the seed data

**Rule:** Before changing any seed or source value, trace ALL downstream models that filter on that value. Use the `impact-analyzer` agent for complex cases.

### Anti-Pattern 2: Dimension Source Collision in UNION ALL

**Symptom:** Same entity appears with different dimension values after UNION ALL.

**Why it happens:** Different CTEs get the same attribute (e.g., `region`) from different upstream models.

**Prevention:** Always source shared dimension attributes from the same canonical dimension table in every CTE of a UNION ALL.

### Anti-Pattern 3: Schema-Only Validation

**Symptom:** Running `dbt build +model+` and assuming correctness because no errors.

**Why it's insufficient:** `dbt test` checks structure, not meaning. A model can pass all schema tests while producing semantically incorrect data (wrong region assignments, inflated aggregations, missing YTD values).

**Prevention:** After significant model changes, run functional test queries (Patterns 1-5 above) to verify semantic correctness.

### Anti-Pattern 4: Untested YTD Accumulation

**Symptom:** Adding window functions for YTD without verifying the PARTITION BY is correct.

**Why it fails:** If PARTITION BY is missing a dimension column (e.g., `metric_section`), values from different categories bleed into each other.

**Prevention:** Always run Pattern 2 after adding or modifying YTD window functions.

---

## Pre-Change Impact Analysis Checklist

Before modifying seeds, sources, or dimension attribute values:

- [ ] **Identify change type:** Additive (new column/row) or mutative (changing existing values)?
- [ ] **If mutative:** List all downstream models using `dbt list --select +model_name --output name`
- [ ] **Search for value-dependent filters:** `grep -r "value_being_changed" models/` across WHERE, CASE, JOIN conditions
- [ ] **Classify dependencies:**
  - Hard: `column = 'value'` (will break if value changes)
  - Soft: `column <> 'value'` (will change behavior if value changes)
  - Pass-through: column used but not filtered (safe to change)
- [ ] **If any hard/soft dependencies exist:** Do NOT change the source. Fix the consumer model instead.
- [ ] **For complex cases:** Delegate to `impact-analyzer` agent

---

## Post-Implementation Validation Checklist

After implementing model changes:

- [ ] **Run schema tests:** `dbt test --select model_name`
- [ ] **Run Pattern 1:** Check for duplicate dimension values on key entities
- [ ] **Run Pattern 2:** If window functions were added/changed, verify YTD accumulation
- [ ] **Run Pattern 3:** If aggregation levels exist, verify cross-level consistency
- [ ] **Run Pattern 4:** If model has UNION ALL, audit dimension source consistency
- [ ] **Run Pattern 5:** Check admin/system entities for anomalies
- [ ] **Build downstream:** `dbt build --select model_name+`
- [ ] **Spot-check downstream:** Run Pattern 1 on downstream models too

---

## Integration with Existing Tests

| Existing Test Type | What It Catches | Gap Functional Tests Fill |
|-------------------|-----------------|--------------------------|
| `unique` test | Duplicate primary keys | Duplicate rows from dimension collisions (different PK, same entity) |
| `not_null` test | Missing values | Semantically wrong values (wrong region, wrong category) |
| `dbt build +model+` | Compilation errors | Data-level incorrectness (wrong aggregations, inflated values) |
| `relationships` test | Orphan foreign keys | Inconsistent dimension attributes across joined models |
| `metric-validation` skill | Metric formula correctness | Source consistency across CTEs feeding the formula |

---

## Memory Integration

After completing functional testing:

1. **Record new anti-patterns:** `.claude/memory/patterns/`
2. **Update dimension source map:** Track which models source each dimension attribute from where
3. **Store validation results:** Include in episode notes for regression comparison