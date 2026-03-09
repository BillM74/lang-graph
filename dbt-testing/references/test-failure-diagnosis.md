# Test Failure Diagnosis & Troubleshooting

Systematic approach to diagnosing and fixing dbt test failures.

## Quick Diagnosis Workflow

```
Test Failed
├─ 1. Identify test type & model
├─ 2. Store failures: dbt test --store-failures
├─ 3. Inspect failing records
├─ 4. Determine root cause
├─ 5. Apply fix
└─ 6. Re-run and verify
```

---

## Common Test Failures

### `unique` Test Failure

**Symptom:** Duplicate values in column that should be unique.

**Common Causes:**
1. **Duplicate source records** - Data quality issue upstream
2. **Missing deduplication** - Join or transformation creates duplicates
3. **Incorrect grain** - Model doesn't match expected grain

**Diagnosis:**
```sql
-- Query stored failures
SELECT column_name, COUNT(*) as duplicate_count
FROM dbt_test_failures.unique_model_name_column_name
GROUP BY column_name
ORDER BY duplicate_count DESC;

-- Find example duplicates
SELECT *
FROM {{ ref('model_name') }}
WHERE column_name IN (
    SELECT column_name
    FROM {{ ref('model_name') }}
    GROUP BY column_name
    HAVING COUNT(*) > 1
)
ORDER BY column_name;
```

**Fixes:**
```sql
-- Option 1: Deduplicate with QUALIFY
SELECT *
FROM source_table
QUALIFY ROW_NUMBER() OVER (PARTITION BY id ORDER BY updated_at DESC) = 1

-- Option 2: Add GROUP BY
SELECT
    id,
    MAX(name) AS name,
    MAX(updated_at) AS updated_at
FROM source_table
GROUP BY id

-- Option 3: Fix upstream data source
-- Report to data team if source has duplicates
```

---

### `not_null` Test Failure

**Symptom:** NULL values in column that should always have data.

**Common Causes:**
1. **Missing data in source** - Data pipeline issue
2. **Incorrect JOIN** - LEFT JOIN creating NULLs
3. **Missing COALESCE** - No default value handling

**Diagnosis:**
```sql
-- Count and inspect NULLs
SELECT COUNT(*) as null_count
FROM {{ ref('model_name') }}
WHERE column_name IS NULL;

-- Find patterns in NULL records
SELECT
    date_column,
    related_field,
    COUNT(*) as null_count
FROM {{ ref('model_name') }}
WHERE column_name IS NULL
GROUP BY 1, 2
ORDER BY 3 DESC;
```

**Fixes:**
```sql
-- Option 1: COALESCE with default
SELECT
    COALESCE(column_name, 'Unknown') AS column_name
FROM source_table

-- Option 2: Filter out NULLs
SELECT *
FROM source_table
WHERE column_name IS NOT NULL

-- Option 3: Fix JOIN type
-- Change LEFT JOIN to INNER JOIN if NULLs unacceptable
SELECT a.*, b.column_name
FROM table_a a
INNER JOIN table_b b  -- Instead of LEFT JOIN
    ON a.id = b.id
```

---

### `relationships` Test Failure

**Symptom:** Foreign key values not found in parent table (orphan records).

**Common Causes:**
1. **Missing parent records** - Parent table incomplete
2. **Timing issue** - Child loaded before parent
3. **Data quality** - Invalid FKs in source

**Diagnosis:**
```sql
-- Find orphan records
SELECT c.*
FROM {{ ref('child_table') }} c
LEFT JOIN {{ ref('parent_table') }} p
    ON c.foreign_key = p.primary_key
WHERE p.primary_key IS NULL;

-- Count by date to find patterns
SELECT
    DATE_TRUNC('day', c.created_at) AS day,
    COUNT(*) as orphan_count
FROM {{ ref('child_table') }} c
LEFT JOIN {{ ref('parent_table') }} p
    ON c.foreign_key = p.primary_key
WHERE p.primary_key IS NULL
GROUP BY 1
ORDER BY 1 DESC;
```

**Fixes:**
```sql
-- Option 1: Filter orphans
SELECT c.*
FROM {{ ref('child_table') }} c
INNER JOIN {{ ref('parent_table') }} p
    ON c.foreign_key = p.primary_key

-- Option 2: Create missing parents (if appropriate)
-- Run parent model first: dbt run --select parent_table+

-- Option 3: Use LEFT JOIN with default
SELECT
    c.*,
    COALESCE(p.parent_name, 'Unknown') AS parent_name
FROM {{ ref('child_table') }} c
LEFT JOIN {{ ref('parent_table') }} p
    ON c.foreign_key = p.primary_key
```

---

### `accepted_values` Test Failure

**Symptom:** Unexpected values in categorical column.

**Common Causes:**
1. **New category added** - Source data changed
2. **Typo or inconsistent casing** - Data quality issue
3. **Test list outdated** - Accepted values need updating

**Diagnosis:**
```sql
-- Find unexpected values
SELECT
    column_name,
    COUNT(*) as occurrence_count
FROM {{ ref('model_name') }}
WHERE column_name NOT IN ('expected1', 'expected2', 'expected3')
GROUP BY 1
ORDER BY 2 DESC;

-- Check recent additions
SELECT
    column_name,
    MIN(created_at) AS first_seen,
    COUNT(*) as count
FROM {{ ref('model_name') }}
GROUP BY 1
ORDER BY 2 DESC;
```

**Fixes:**
```yaml
# Option 1: Update accepted values list
- name: status
  tests:
    - accepted_values:
        values: ['active', 'inactive', 'pending', 'new_status']  # Add new value

# Option 2: Standardize with CASE
SELECT
    CASE
        WHEN LOWER(status) = 'active' THEN 'active'
        WHEN LOWER(status) = 'inactive' THEN 'inactive'
        ELSE 'unknown'
    END AS status
FROM source_table
```

---

### `expression_is_true` Test Failure

**Symptom:** Business rule validation failed.

**Common Causes:**
1. **Calculation error** - Logic bug in model
2. **Data anomaly** - Unexpected edge case
3. **Test too strict** - Rule doesn't account for all scenarios

**Diagnosis:**
```sql
-- Find violating records
SELECT *
FROM {{ ref('model_name') }}
WHERE NOT (expression_that_should_be_true);

-- Example: Amount validation
SELECT *
FROM {{ ref('fct_orders') }}
WHERE amount < 0;  -- Should all be non-negative

-- Example: Date range validation
SELECT *
FROM {{ ref('fct_orders') }}
WHERE ship_date < order_date;  -- Ship should be after order
```

**Fixes:**
```sql
-- Option 1: Fix calculation
SELECT
    CASE
        WHEN calculated_amount < 0 THEN 0
        ELSE calculated_amount
    END AS amount

-- Option 2: Filter invalid records
SELECT *
FROM source_table
WHERE amount >= 0  -- Remove negatives

-- Option 3: Update test to handle edge cases
tests:
  - dbt_utils.expression_is_true:
      expression: "amount >= 0 OR status = 'refunded'"  -- Allow negatives for refunds
```

---

## Testing Incremental Models

### Idempotency Issues

**Problem:** Running incremental twice creates duplicates.

**Diagnosis:**
```bash
# Run model twice
dbt run --select model_name
dbt run --select model_name  # No --full-refresh

# Check for duplicates
dbt test --select model_name
```

**Fix:**
```sql
-- Ensure proper unique_key
{{
    config(
        materialized='incremental',
        unique_key='id',  # Must be truly unique
        incremental_strategy='merge'
    )
}}
```

### Late-Arriving Data

**Problem:** Incremental missing recent updates.

**Fix:**
```sql
{% if is_incremental() %}
    -- Add lookback window
    WHERE updated_at > (
        SELECT DATEADD(day, -3, MAX(updated_at))
        FROM {{ this }}
    )
{% endif %}
```

---

## Stored Failures Inspection

### Enable Storage

```yaml
# dbt_project.yml
tests:
  +store_failures: true
  +schema: dbt_test_failures
```

### Query Failures

```sql
-- List all failure tables
SHOW TABLES IN dbt_test_failures;

-- Inspect specific failure
SELECT * FROM dbt_test_failures.unique_fct_orders_order_id
LIMIT 100;

-- Count failures over time
SELECT
    DATE_TRUNC('day', dbt_updated_at) AS day,
    COUNT(*) as failure_count
FROM dbt_test_failures.unique_fct_orders_order_id
GROUP BY 1
ORDER BY 1 DESC;
```

---

## Common Fixes Summary

| Test Type | Common Fix | Implementation |
|-----------|-----------|----------------|
| `unique` | Deduplicate with QUALIFY | `QUALIFY ROW_NUMBER() OVER (...) = 1` |
| `not_null` | COALESCE default | `COALESCE(col, 'Unknown')` |
| `relationships` | Filter orphans | Use INNER JOIN instead of LEFT |
| `accepted_values` | Update list or standardize | Add value or use CASE |
| `expression_is_true` | Fix logic or filter | Correct calculation or WHERE clause |

---

## Prevention Checklist

Before deploying models:

- [ ] Test locally first (`dbt test --select model_name`)
- [ ] Check test coverage (use `scripts/test-coverage-check.sh`)
- [ ] Enable `store_failures` for easier diagnosis
- [ ] Review dbt run logs for warnings
- [ ] Validate with `dbt show` before full run
- [ ] Check upstream data quality if failures persist

---

## Escalation Guide

### Fix Yourself If:
- Test failure is in model you created
- Clear logic error or typo
- Missing accepted value (just add it)
- Simple filter fix

### Escalate to Data Owner If:
- Source data quality issue
- Unclear business rule
- Systemic data problem
- Needs upstream fix

### Escalate to Architect If:
- Model design issue
- Grain mismatch across models
- Complex referential integrity problem
- Needs architectural change

---

## Memory Integration

**Before troubleshooting:**
Check `.claude/memory/patterns/common-test-failures.json` for similar past failures.

**After fixing:**
If novel failure pattern, add to common-test-failures.json with:
- Test type
- Root cause
- Fix applied
- Prevention tip
