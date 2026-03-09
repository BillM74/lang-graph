---
name: data-quality-debugging
description: Systematic approach to diagnosing and fixing dbt test failures and data quality issues. Use when: "test failed", "test is failing", "why did this fail", "broken test", "fix test failure", "dbt test error", "unique test failed", "not_null failed", "relationship test failed", "data quality issue"
---

# Data Quality Debugging

Systematic approach to diagnosing and fixing dbt test failures and data quality issues.

## Quick Diagnosis Workflow

```
TEST FAILED
    │
    ├─► What type of test failed?
    │   ├─► unique → Duplicate Investigation
    │   ├─► not_null → NULL Source Analysis
    │   ├─► relationships → Orphan Record Check
    │   ├─► accepted_values → Value Drift Analysis
    │   └─► custom/generic → Read test definition
    │
    ├─► Get failing records
    │   dbt test --select model_name --store-failures
    │   SELECT * FROM <schema>_dbt_test__audit.<test_name>
    │
    └─► Trace to source
        Follow lineage backwards to find where issue originates
```

---

## Test Failure Types & Fixes

### 1. Unique Test Failures

**Symptoms**: `unique` test fails on primary key column

**Diagnosis Query**:
```sql
-- Find duplicates
SELECT
    primary_key_column,
    COUNT(*) as duplicate_count
FROM {{ ref('model_name') }}
GROUP BY 1
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC
LIMIT 20;

-- See full duplicate records
WITH duplicates AS (
    SELECT primary_key_column
    FROM {{ ref('model_name') }}
    GROUP BY 1
    HAVING COUNT(*) > 1
)
SELECT m.*
FROM {{ ref('model_name') }} m
JOIN duplicates d ON m.primary_key_column = d.primary_key_column
ORDER BY m.primary_key_column;
```

**Common Causes & Fixes**:

| Cause | How to Identify | Fix |
|-------|-----------------|-----|
| Fan-out join | Row count increased after JOIN | Add DISTINCT or fix join keys |
| Missing grain column | Same entity appears multiple times | Add missing dimension to PK |
| Source duplicates | Duplicates exist in source | Add QUALIFY ROW_NUMBER() |
| Incremental overlap | Same records in multiple batches | Fix incremental logic |

**Fix Patterns**:

```sql
-- Fix 1: Deduplicate with QUALIFY
SELECT *
FROM source_table
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY primary_key
    ORDER BY updated_at DESC
) = 1

-- Fix 2: Fix fan-out join (1:many → 1:1)
-- WRONG: Creates duplicates
SELECT o.*, c.*
FROM orders o
LEFT JOIN customers c ON o.customer_id = c.id

-- RIGHT: Pre-aggregate or use scalar subquery
SELECT
    o.*,
    c.customer_name,
    (SELECT COUNT(*) FROM orders WHERE customer_id = o.customer_id) as order_count
FROM orders o
LEFT JOIN customers c ON o.customer_id = c.id
```

---

### 2. Not Null Test Failures

**Symptoms**: `not_null` test fails on required column

**Diagnosis Query**:
```sql
-- Find NULL records
SELECT *
FROM {{ ref('model_name') }}
WHERE required_column IS NULL
LIMIT 20;

-- Count NULLs by source
SELECT
    source_system,
    COUNT(*) as null_count,
    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () as pct
FROM {{ ref('model_name') }}
WHERE required_column IS NULL
GROUP BY 1
ORDER BY null_count DESC;
```

**Common Causes & Fixes**:

| Cause | How to Identify | Fix |
|-------|-----------------|-----|
| LEFT JOIN orphans | NULLs only in joined columns | Change to INNER JOIN or COALESCE |
| Source data gap | NULLs exist in source | Add source test or COALESCE default |
| Late-arriving data | NULLs in recent records only | Wait for data or mark as pending |
| Logic error | NULLs from CASE WHEN | Add ELSE clause |

**Fix Patterns**:

```sql
-- Fix 1: COALESCE with default
SELECT
    COALESCE(status, 'unknown') as status

-- Fix 2: Filter NULLs (if legitimately excludable)
SELECT *
FROM source
WHERE required_field IS NOT NULL

-- Fix 3: Add ELSE to CASE
SELECT
    CASE
        WHEN condition_a THEN 'A'
        WHEN condition_b THEN 'B'
        ELSE 'other'  -- Don't forget this!
    END as category
```

---

### 3. Relationship Test Failures

**Symptoms**: `relationships` test fails (orphan records)

**Diagnosis Query**:
```sql
-- Find orphan records
SELECT
    child.foreign_key,
    COUNT(*) as orphan_count
FROM {{ ref('child_model') }} child
LEFT JOIN {{ ref('parent_model') }} parent
    ON child.foreign_key = parent.primary_key
WHERE parent.primary_key IS NULL
  AND child.foreign_key IS NOT NULL
GROUP BY 1
ORDER BY orphan_count DESC
LIMIT 20;

-- See orphan record details
SELECT child.*
FROM {{ ref('child_model') }} child
LEFT JOIN {{ ref('parent_model') }} parent
    ON child.foreign_key = parent.primary_key
WHERE parent.primary_key IS NULL
  AND child.foreign_key IS NOT NULL
LIMIT 100;
```

**Common Causes & Fixes**:

| Cause | How to Identify | Fix |
|-------|-----------------|-----|
| Timing mismatch | Parent loaded after child | Fix DAG order or use incremental |
| Soft deletes | Parent deleted but child remains | Filter deleted parents |
| Data type mismatch | FK is string, PK is int | Cast types consistently |
| Partial load | Parent filter excludes some | Align WHERE clauses |

**Fix Patterns**:

```sql
-- Fix 1: Add WHERE clause to exclude orphans
SELECT *
FROM orders
WHERE customer_id IN (SELECT id FROM customers)

-- Fix 2: Cast data types
SELECT
    CAST(customer_id AS VARCHAR) as customer_id

-- Fix 3: Include soft-deleted parents in lookup
-- In parent model
SELECT * FROM source WHERE deleted_at IS NULL
-- Should be
SELECT * FROM source  -- Include all for relationship integrity
```

---

### 4. Accepted Values Test Failures

**Symptoms**: `accepted_values` test fails (unexpected value)

**Diagnosis Query**:
```sql
-- Find unexpected values
SELECT
    status_column,
    COUNT(*) as count
FROM {{ ref('model_name') }}
WHERE status_column NOT IN ('expected', 'values', 'list')
GROUP BY 1
ORDER BY count DESC;

-- See records with unexpected values
SELECT *
FROM {{ ref('model_name') }}
WHERE status_column NOT IN ('expected', 'values', 'list')
LIMIT 20;
```

**Common Causes & Fixes**:

| Cause | How to Identify | Fix |
|-------|-----------------|-----|
| New valid value | Business added new status | Update accepted_values list |
| Typo in source | Similar to valid value | Add source cleanup |
| Case mismatch | 'Active' vs 'active' | Normalize with UPPER/LOWER |
| NULL value | NULL not in list | Add `quote: false` for NULL |

**Fix Patterns**:

```sql
-- Fix 1: Normalize values
SELECT
    UPPER(TRIM(status)) as status

-- Fix 2: Map unexpected to valid
SELECT
    CASE status
        WHEN 'actv' THEN 'active'
        WHEN 'Active' THEN 'active'
        ELSE status
    END as status

-- Fix 3: Update test to include new valid value
# In schema.yml
- accepted_values:
    values: ['active', 'inactive', 'pending', 'new_status']
```

---

## Debugging Commands

### Store Failures for Investigation

```bash
# Run tests and store failures
dbt test --select model_name --store-failures

# Query stored failures
# Results in: <target_schema>_dbt_test__audit.<test_name>
```

### Trace Lineage to Source

```bash
# Find upstream models
dbt list --select +model_name --output name

# Check what feeds into the failing model
dbt list --select +model_name --resource-type model
```

### Compare Row Counts

```sql
-- Quick sanity check across pipeline
SELECT 'staging' as layer, COUNT(*) FROM stg_orders
UNION ALL
SELECT 'activity' as layer, COUNT(*) FROM orders_placed
UNION ALL
SELECT 'entity' as layer, COUNT(*) FROM dim_orders;
```

---

## Prevention Checklist

### At Source (Staging)

- [ ] Add `not_null` tests on columns that should never be NULL
- [ ] Add `unique` test if source should have unique keys
- [ ] Add `accepted_values` for known categorical fields
- [ ] Document expected NULLs and why they're acceptable

### At Transform (Activities/Entities)

- [ ] Verify grain hasn't changed (row count check)
- [ ] Test PK uniqueness before adding FK relationships
- [ ] Add relationship tests for all foreign keys
- [ ] Use COALESCE for columns that must have values

### At Consumption (Marts/Nets)

- [ ] Verify aggregations sum correctly
- [ ] Test that filters don't exclude valid data
- [ ] Add range tests for metrics (e.g., percentages 0-100)

---

## Common Anti-Patterns

### Anti-Pattern 1: Suppressing Tests Instead of Fixing

```yaml
# BAD: Hiding the problem
- unique:
    config:
      severity: warn  # Just to make CI pass

# GOOD: Fix or document why it's acceptable
- unique:
    config:
      # Duplicates expected due to SCD Type 2
      # Use surrogate_key instead for uniqueness
      enabled: false
```

### Anti-Pattern 2: Testing Too Late

```
WRONG: Source → Transform → Transform → Test

RIGHT: Source → Test → Transform → Test → Transform → Test
       (Test at each layer)
```

### Anti-Pattern 3: Ignoring Warnings

```bash
# Don't ignore these
dbt test 2>&1 | grep -i warn

# Warnings often become failures when:
# - Data volume increases
# - Edge cases appear
# - Upstream systems change
```

---

## Escalation Guide

### When to Fix Yourself
- Test logic is wrong (test definition error)
- Transform logic is wrong (SQL bug)
- Data type mismatch (casting issue)

### When to Escalate to Data Source Owner
- Source data has unexpected NULLs
- Source has duplicates that shouldn't exist
- New values appearing without documentation

### When to Escalate to Data Architect
- Grain is fundamentally wrong
- Relationship model is incorrect
- Need to redesign for data quality

---

## Quick Reference: Test → Likely Cause → First Check

| Test | Likely Cause | First Check |
|------|--------------|-------------|
| `unique` fails | Fan-out join | Compare row counts before/after JOIN |
| `not_null` fails | LEFT JOIN orphan | Check if NULLs only in joined columns |
| `relationships` fails | Timing/filter mismatch | Compare date ranges in both models |
| `accepted_values` fails | New valid value | Ask if business added new status |
| Row count changed | Filter or join change | Diff the SQL between versions |
| Metrics don't match | Aggregation logic | Check GROUP BY and filters |

---

## Memory Integration

### Before Debugging

Check known patterns first:

1. **Query failure patterns**: `.claude/memory/patterns/common-test-failures.json`
   - "Have we seen this test failure before?"
   - "What was the root cause last time?"

2. **Review past debugging sessions**: `.claude/memory/episodes/`
   - "How did we solve similar issues?"

### Root Cause Memory

When investigating, check these common causes from this project:

| Test Failure | Past Root Causes | Check Query |
|--------------|------------------|-------------|
| `unique` on PK | Fan-out join in enrichment | Row count before/after join |
| `not_null` on FK | LEFT JOIN orphans | Count nulls after join |
| `relationships` | Timing mismatch | Compare max dates |
| `accepted_values` | New business status | Query distinct values |

### After Debugging

**Always store the resolution:**

1. **Update failure patterns**: `.claude/memory/patterns/common-test-failures.json`
   ```json
   {
     "failure_type": "unique_test_fct_orders",
     "model": "fct_orders",
     "column": "order_id",
     "root_cause": "Join to dim_customers caused fan-out due to SCD2",
     "fix": "Added QUALIFY to pick current customer record only",
     "date_discovered": "2026-01-14",
     "prevention": "Always use is_current = true when joining SCDs"
   }
   ```

2. **Store episode**: `.claude/memory/episodes/`
   ```markdown
   ## Debug Session - [Model] Test Failure

   **Date:** YYYY-MM-DD
   **Test:** [test name]
   **Model:** [model name]

   **Symptoms:**
   - [What was observed]

   **Investigation Steps:**
   1. [Step 1]
   2. [Step 2]

   **Root Cause:**
   - [What was wrong]

   **Fix Applied:**
   - [Code change]

   **Prevention:**
   - [How to prevent recurrence]
   ```

### Prevention Checklist from Past Issues

Based on past debugging in this project:

- [ ] When joining to SCD2 dims, always filter `is_current = true`
- [ ] When using LEFT JOIN, check for unexpected NULLs
- [ ] When adding new sources, verify no duplicates in source
- [ ] When changing filters, verify row count didn't change unexpectedly
- [ ] When adding new status values, update `accepted_values` tests

### Learning Loop

After each debug session:

1. **Ask**: "Could this have been caught earlier?"
2. **If yes**: Add upstream test or validation
3. **Update patterns**: Add to failure patterns for faster future diagnosis
4. **Share learning**: Update team documentation if pattern is common
