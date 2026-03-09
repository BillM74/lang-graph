---
name: metric-validation
description: Metric validation procedures and discrepancy troubleshooting. Use when: "metrics don't match", "numbers are wrong", "reconcile reports", "audit KPI", "validate calculation", "variance investigation", "Power BI vs Snowflake difference", "why doesn't this add up", "metric discrepancy", "wrong total", "numbers don't reconcile"
---

# Metric Validation Guide

Procedures for validating metric calculations and troubleshooting discrepancies.

## Validation Framework

### 1. Definition Check
Before validating calculations, confirm the metric is well-defined:

- [ ] Clear, unambiguous name
- [ ] Formula/calculation documented
- [ ] Business definition exists
- [ ] Owner identified
- [ ] Filters specified
- [ ] Dimensions documented
- [ ] Atomic vs compound classified

### 2. Calculation Validation

**Compare source of truth vs. reporting:**

```sql
with

-- Source of truth (raw calculation)
truth as (
    select
        date_month,
        sum(mrr_amount) as mrr_truth
    from {{ ref('fct_subscriptions') }}
    where subscription_status = 'active'
    group by 1
),

-- Dashboard/report version
dashboard as (
    select
        date_month,
        mrr as mrr_dashboard
    from {{ ref('net_mrr_metrics') }}
),

-- Compare
comparison as (
    select
        t.date_month,
        t.mrr_truth,
        d.mrr_dashboard,
        t.mrr_truth - d.mrr_dashboard as variance,
        abs(t.mrr_truth - d.mrr_dashboard) / nullif(t.mrr_truth, 0) * 100 as pct_variance
    from truth t
    left join dashboard d using (date_month)
)

select * from comparison
where abs(pct_variance) > 1  -- Flag >1% variance
order by date_month desc
```

### 3. Cross-Validation Tests

**Compound metric matches components:**
```sql
-- tests/assert_cac_formula.sql
select *
from {{ ref('net_acquisition_metrics') }}
where abs(
    cac - (sales_marketing_spend / nullif(new_customers, 0))
) > 0.01
```

**Metrics sum correctly:**
```sql
-- MRR components should sum to total
select *
from {{ ref('net_mrr_metrics') }}
where abs(
    total_mrr - (new_mrr + expansion_mrr - contraction_mrr - churned_mrr)
) > 0.01
```

---

## Troubleshooting Discrepancies

### Systematic Investigation Process

**Step 1: Confirm the Question**
- What exactly is being compared?
- What's the expected value vs actual?
- Which reports/dashboards show discrepancies?
- What time period?

**Step 2: Check Definitions**
| Question | Impact |
|----------|--------|
| Same metric definition? | Different formulas = different results |
| Same filters applied? | Missing filter = inflated numbers |
| Same date range logic? | Fiscal vs calendar year |
| Same granularity? | Daily vs monthly aggregation |

**Step 3: Trace to Source**
```sql
-- Trace metric back to source tables
-- Check each transformation step

-- Step 1: Raw source count
select count(*) from raw.orders;

-- Step 2: Staging count
select count(*) from {{ ref('stg_orders') }};

-- Step 3: Fact count
select count(*) from {{ ref('fct_orders') }};

-- Step 4: Metric calculation
select sum(order_amount) from {{ ref('fct_orders') }};
```

**Step 4: Identify Root Cause**

| Symptom | Likely Cause | How to Verify |
|---------|--------------|---------------|
| Values differ by small % | Rounding differences | Check decimal precision |
| Values differ by exact amount | Missing/extra filter | Compare filter logic |
| Values differ by multiplier | Different aggregation level | Check GROUP BY |
| One report is stale | Data freshness | Check _loaded_at timestamps |
| Values match sometimes | Timing window differences | Compare date logic |

---

## Common Discrepancy Causes

### 1. Date/Time Issues

**Problem:** Different date filters or timezone handling

```sql
-- Check: Are both using same date logic?

-- Report A: Uses created_at
where created_at >= '2024-01-01'

-- Report B: Uses updated_at
where updated_at >= '2024-01-01'

-- Fix: Standardize on one timestamp field
```

### 2. Filter Differences

**Problem:** Different filtering logic

```sql
-- Check: Are all filters applied consistently?

-- Report A: Active customers only
where customer_status = 'active'

-- Report B: All customers (including churned)
-- No filter!

-- Fix: Document and apply consistent filters
```

### 3. Aggregation Level

**Problem:** Different GROUP BY granularity

```sql
-- Check: Same aggregation level?

-- Report A: Customer level
select customer_id, sum(revenue)
group by customer_id

-- Report B: Order level (double counts customers)
select customer_id, order_id, revenue
-- No aggregation!

-- Fix: Align on correct grain
```

### 4. Data Freshness

**Problem:** Reports using data from different times

```sql
-- Check: When was data last loaded?
select
    max(_loaded_at) as last_load,
    max(updated_at) as last_update
from {{ ref('fct_orders') }}
```

### 5. Duplicate Records

**Problem:** Duplicates in source causing inflation

```sql
-- Check: Are there duplicates?
select
    order_id,
    count(*) as cnt
from {{ ref('fct_orders') }}
group by 1
having count(*) > 1
```

### 6. Incomplete Joins

**Problem:** LEFT JOIN dropping records or creating duplicates

```sql
-- Check: Join behavior
select
    count(*) as total_orders,
    count(c.customer_id) as matched_customers,
    count(*) - count(c.customer_id) as unmatched
from orders o
left join customers c on o.customer_id = c.customer_id
```

---

## Metric Quality Tests

### Required Tests for Metrics

```yaml
# schema.yml
models:
  - name: net_revenue_metrics
    description: Pre-computed revenue metrics

    # Model-level tests
    tests:
      # Grain uniqueness
      - dbt_utils.unique_combination_of_columns:
          combination_of_columns:
            - date_month
            - customer_segment
            - product_tier

    columns:
      - name: mrr
        description: Monthly Recurring Revenue
        tests:
          - not_null
          # MRR should be non-negative
          - dbt_utils.expression_is_true:
              expression: ">= 0"

      - name: customer_count
        tests:
          - not_null
          - dbt_utils.expression_is_true:
              expression: ">= 0"

      - name: arpu
        description: Average Revenue Per User (MRR / customers)
        tests:
          # ARPU should be reasonable
          - dbt_utils.expression_is_true:
              expression: "arpu >= 0 or arpu is null"
              config:
                severity: warn
```

### Variance Monitoring

```sql
-- tests/assert_mrr_reasonable_variance.sql
-- MRR should not change >50% month-over-month

with monthly_changes as (
    select
        date_month,
        mrr,
        lag(mrr) over (order by date_month) as prev_mrr,
        abs(mrr - lag(mrr) over (order by date_month))
            / nullif(lag(mrr) over (order by date_month), 0) as pct_change
    from {{ ref('net_mrr_metrics') }}
)

select *
from monthly_changes
where pct_change > 0.5
  and prev_mrr > 0  -- Ignore first month
```

---

## Validation Checklist

### Before Deploying a New Metric

- [ ] **Definition documented** - Formula, filters, business meaning
- [ ] **Matches existing reports** - If replacing, values align
- [ ] **Edge cases handled** - Nulls, zeros, divide-by-zero
- [ ] **Tests added** - Uniqueness, not null, range checks
- [ ] **Stakeholder validated** - Business owner confirms correctness
- [ ] **Historical data verified** - Spot-check multiple periods

### When Investigating a Discrepancy

- [ ] **Reproduced the issue** - Confirmed in multiple places
- [ ] **Traced to source** - Identified which step diverges
- [ ] **Root cause identified** - Know why the difference exists
- [ ] **Fix implemented** - Corrected the calculation
- [ ] **Verified fix** - Values now match
- [ ] **Documented** - Explained what was wrong and how it was fixed

---

## MCP Tools for Validation

Use these MCP tools to validate metrics:

| Task | MCP Tool |
|------|----------|
| Run validation query | `mcp__snowflake__run_snowflake_query` |
| Check table structure | `mcp__snowflake__describe_object` |
| Preview metric model | `mcp__dbt__show` |
| Run metric tests | `mcp__dbt__test` |
| Check model lineage | `mcp__dbt__get_model_lineage_dev` |

**Example: Validate MRR calculation**
```sql
-- Use mcp__snowflake__run_snowflake_query with:
select
    date_trunc('month', subscription_date)::date as date_month,
    sum(mrr_amount) as calculated_mrr
from analytics.fct_subscriptions
where subscription_status = 'active'
group by 1
order by 1 desc
limit 12
```

---

## Memory Integration

### Before Validating

Check for known patterns:

1. **Review past validations**: `.claude/memory/reflections/metrics/`
   - "What issues have we found with this metric before?"
   - "What validation queries worked well?"

2. **Check common discrepancy causes**: `.claude/memory/patterns/common-test-failures.json`
   - Known issues may already be documented

### Standard Reconciliation Queries

**Source-to-Target Reconciliation Template:**
```sql
-- Compare source system to analytics layer
WITH source AS (
    SELECT
        date_trunc('month', created_at) as period,
        count(distinct customer_id) as source_count
    FROM raw.source_system.customers
    GROUP BY 1
),
target AS (
    SELECT
        date_month as period,
        new_customers as target_count
    FROM analytics.net_customer_metrics
)
SELECT
    coalesce(s.period, t.period) as period,
    s.source_count,
    t.target_count,
    s.source_count - t.target_count as variance,
    abs(s.source_count - t.target_count) / nullif(s.source_count, 0) * 100 as pct_variance
FROM source s
FULL OUTER JOIN target t ON s.period = t.period
WHERE abs(pct_variance) > 1
ORDER BY period DESC;
```

### After Validating

**Document findings:**

1. **If discrepancy found**, add to patterns:
   ```json
   // .claude/memory/patterns/common-test-failures.json
   {
     "metric_validation": {
       "metric": "metric_name",
       "discrepancy": "description",
       "root_cause": "what caused it",
       "fix": "how it was resolved",
       "date": "2026-01-14"
     }
   }
   ```

2. **Store reflection**: `.claude/memory/reflections/metrics/`
   ```markdown
   ## Validation - [Metric Name]

   **Date:** YYYY-MM-DD
   **Result:** Pass/Fail
   **Variance Found:** X%
   **Root Cause:** [If applicable]
   **Fix Applied:** [If applicable]
   ```

### Common Discrepancy Patterns in This Project

| Metric | Common Issue | Typical Cause |
|--------|-------------|---------------|
| MRR | ~1-2% variance | Proration timing |
| New Customers | Exact count off | Filter on first_order vs signup |
| Churn | Higher than expected | Soft deletes not excluded |
| CAC | Varies by period | Expense accrual timing |

When investigating, check these patterns first.