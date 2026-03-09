---
name: incremental-strategies
description: dbt incremental model strategies and patterns. Use when: "make this incremental", "slow build", "full refresh", "should I use incremental", "incremental vs table", "append strategy", "merge strategy", "delete+insert", "incremental model", "optimize build time", "large table materialization"
---

# Incremental Model Strategies

Guide for choosing and implementing incremental materialization in dbt for Snowflake.

## When to Use Incremental

### Decision Matrix

```
Is the table > 1GB or takes > 30 seconds to build?
├── No → Use VIEW or TABLE
└── Yes
    └── Does the data have a reliable timestamp for changes?
        ├── No → Use TABLE (consider partitioning)
        └── Yes
            └── Do records get updated after initial insert?
                ├── No → Use APPEND strategy
                └── Yes → Use MERGE strategy
```

### Use Incremental When:
- Table is large (>1GB or millions of rows)
- Full rebuilds take too long (>30 seconds)
- Data has a reliable timestamp (`updated_at`, `created_at`, `event_timestamp`)
- You can identify new/changed records

### Don't Use Incremental When:
- Small tables (<1GB)
- Transformations are complex and order-dependent
- No reliable way to identify changes
- Data frequently requires full recalculation

## Strategy Comparison

| Strategy | Best For | Speed | Complexity |
|----------|----------|-------|------------|
| `append` | Immutable events, logs | Fastest | Lowest |
| `merge` | Records that update | Moderate | Medium |
| `delete+insert` | Partition replacement | Moderate | Medium |

---

## Append Strategy

**Use when:** Data is immutable (events, logs, activities). Records are never updated after creation.

```sql
{{
    config(
        materialized='incremental',
        incremental_strategy='append'
    )
}}

select
    event_id,
    user_id,
    event_type,
    event_timestamp,
    event_properties
from {{ ref('stg_events') }}

{% if is_incremental() %}
    where event_timestamp > (select max(event_timestamp) from {{ this }})
{% endif %}
```

**Pros:**
- Fastest strategy (just INSERT)
- No deduplication overhead
- Simple implementation

**Cons:**
- Cannot handle updates
- Duplicates if run multiple times on same data
- Requires truly immutable data

**Best for:**
- Activity streams (`act_*` models)
- Event logs
- Audit tables
- Clickstream data

---

## Merge Strategy

**Use when:** Records can be updated after initial creation. Need to upsert based on a unique key.

```sql
{{
    config(
        materialized='incremental',
        incremental_strategy='merge',
        unique_key='order_id'
    )
}}

select
    order_id,
    customer_id,
    order_status,
    order_amount,
    updated_at
from {{ ref('stg_orders') }}

{% if is_incremental() %}
    where updated_at > (select max(updated_at) from {{ this }})
{% endif %}
```

**With composite unique key:**
```sql
{{
    config(
        materialized='incremental',
        incremental_strategy='merge',
        unique_key=['order_id', 'line_item_id']
    )
}}
```

**Pros:**
- Handles updates and inserts
- Maintains unique records
- Most flexible strategy

**Cons:**
- Slower than append (requires MERGE operation)
- Needs reliable unique_key
- Higher compute cost

**Best for:**
- Entity tables (customers, orders, products)
- Any data with updates
- Slowly changing dimensions (Type 1)

---

## Delete+Insert Strategy

**Use when:** You want to replace entire partitions or time periods. Useful when corrections affect historical data.

```sql
{{
    config(
        materialized='incremental',
        incremental_strategy='delete+insert',
        unique_key='date_day'
    )
}}

select
    date_day,
    customer_segment,
    sum(revenue) as daily_revenue,
    count(distinct customer_id) as customer_count
from {{ ref('fct_orders') }}
group by 1, 2

{% if is_incremental() %}
    -- Reprocess last 3 days (handles late-arriving data)
    where date_day >= dateadd(day, -3, current_date())
{% endif %}
```

**Pros:**
- Clean partition replacement
- Good for aggregated data
- Handles late-arriving data well

**Cons:**
- Deletes then inserts (two operations)
- Must delete entire partition/key value
- Not for high-cardinality unique keys

**Best for:**
- Daily aggregations
- Metric nets with bi-temporal data
- When you need to reprocess time windows

---

## Incremental Predicate Patterns

### Basic Timestamp Pattern
```sql
{% if is_incremental() %}
    where updated_at > (select max(updated_at) from {{ this }})
{% endif %}
```

### Lookback Window (for late-arriving data)
```sql
{% if is_incremental() %}
    -- 3-day lookback for late data
    where updated_at >= dateadd(day, -3, (select max(updated_at) from {{ this }}))
{% endif %}
```

### Date Partition Pattern
```sql
{% if is_incremental() %}
    -- Only process recent partitions
    where date_day >= (select max(date_day) from {{ this }})
{% endif %}
```

### Multiple Conditions
```sql
{% if is_incremental() %}
    where (
        updated_at > (select max(updated_at) from {{ this }})
        or created_at > (select max(created_at) from {{ this }})
    )
{% endif %}
```

### Variable-based Lookback
```sql
{% set lookback_days = var('incremental_lookback_days', 3) %}

{% if is_incremental() %}
    where event_date >= dateadd(day, -{{ lookback_days }}, current_date())
{% endif %}
```

---

## Unique Key Selection

### Good Unique Keys
```sql
-- Single natural key
unique_key='order_id'

-- Composite key for grain
unique_key=['customer_id', 'subscription_id', 'period_start_date']

-- Surrogate key (when natural key is complex)
unique_key='order_line_sk'  -- Generated with dbt_utils.generate_surrogate_key()
```

### Bad Unique Keys
```sql
-- Too wide (performance impact)
unique_key=['col1', 'col2', 'col3', 'col4', 'col5', 'col6']

-- Non-deterministic
unique_key='row_number'  -- Changes every run!

-- High cardinality for delete+insert
unique_key='transaction_id'  -- Creates millions of small deletes
```

---

## Handling Schema Changes

```sql
{{
    config(
        materialized='incremental',
        unique_key='order_id',
        on_schema_change='sync_all_columns'  -- Recommended
    )
}}
```

| Option | Behavior |
|--------|----------|
| `ignore` | Ignore new columns (default) |
| `fail` | Fail if schema changes |
| `append_new_columns` | Add new columns, keep old |
| `sync_all_columns` | Match source schema exactly |

**Recommendation:** Use `sync_all_columns` for most cases, or `fail` for critical models.

---

## Full Refresh Considerations

### When to Force Full Refresh
```bash
# Rebuild entire table
dbt run --select model_name --full-refresh

# After schema changes
dbt run --select model_name --full-refresh

# After logic changes that affect historical data
dbt run --select model_name --full-refresh
```

### Designing for Occasional Full Refresh
```sql
{{
    config(
        materialized='incremental',
        unique_key='order_id',
        -- Allow full refresh on Sundays
        full_refresh=env_var('DBT_FULL_REFRESH', 'false') == 'true'
    )
}}
```

---

## Testing Incremental Models

### Test for Duplicates
```yaml
models:
  - name: fct_orders
    columns:
      - name: order_id
        tests:
          - unique
          - not_null
```

### Test for Data Loss
```sql
-- tests/assert_incremental_not_losing_data.sql
-- Compare row counts between incremental and full refresh
{% set full_refresh_count = run_query("select count(*) from " ~ ref('fct_orders')) %}
{% set incremental_count = run_query("select count(*) from " ~ this) %}

select 1
where {{ full_refresh_count }} > {{ incremental_count }} * 1.1  -- Allow 10% variance
```

### Test Incremental Logic
```sql
-- Run model twice with same data, ensure no duplicates
-- This catches issues with non-idempotent incremental logic
```

---

## Common Mistakes & Fixes

### 1. Missing is_incremental() Check
```sql
-- Bad: Always filters (even on full refresh)
where updated_at > (select max(updated_at) from {{ this }})

-- Good: Only filter on incremental runs
{% if is_incremental() %}
    where updated_at > (select max(updated_at) from {{ this }})
{% endif %}
```

### 2. No Lookback for Late Data
```sql
-- Bad: Misses late-arriving data
where event_timestamp > (select max(event_timestamp) from {{ this }})

-- Good: 3-day lookback window
where event_timestamp >= dateadd(day, -3, (select max(event_timestamp) from {{ this }}))
```

### 3. Wrong Strategy for Data Type
```sql
-- Bad: Using append for data that updates
-- Results in duplicates when records are updated

-- Good: Use merge for data that updates
{{
    config(
        incremental_strategy='merge',
        unique_key='customer_id'
    )
}}
```

### 4. Forgetting unique_key for Merge
```sql
-- Bad: Merge without unique_key
{{
    config(
        materialized='incremental',
        incremental_strategy='merge'
        -- Missing unique_key!
    )
}}

-- Good: Always specify unique_key for merge
{{
    config(
        materialized='incremental',
        incremental_strategy='merge',
        unique_key='order_id'
    )
}}
```

### 5. Non-deterministic Incremental Logic
```sql
-- Bad: Results vary based on when you run
where created_at > current_date() - 7

-- Good: Deterministic based on existing data
where created_at > (select max(created_at) from {{ this }})
```

---

## Performance Optimization

### Cluster Incremental Tables
```sql
{{
    config(
        materialized='incremental',
        unique_key='order_id',
        cluster_by=['order_date', 'customer_segment']
    )
}}
```

### Partition by Date (delete+insert)
```sql
{{
    config(
        materialized='incremental',
        incremental_strategy='delete+insert',
        unique_key='date_day',  -- Partition key
        cluster_by=['customer_segment']
    )
}}
```

### Use Transient for Staging
```sql
{{
    config(
        materialized='incremental',
        transient=true  -- No fail-safe storage costs
    )
}}
```

---

## Quick Reference

### Minimal Append Model
```sql
{{ config(materialized='incremental', incremental_strategy='append') }}

select * from {{ ref('stg_events') }}
{% if is_incremental() %}
    where event_timestamp > (select max(event_timestamp) from {{ this }})
{% endif %}
```

### Minimal Merge Model
```sql
{{ config(materialized='incremental', incremental_strategy='merge', unique_key='id') }}

select * from {{ ref('stg_entities') }}
{% if is_incremental() %}
    where updated_at > (select max(updated_at) from {{ this }})
{% endif %}
```

### Minimal Delete+Insert Model
```sql
{{ config(materialized='incremental', incremental_strategy='delete+insert', unique_key='date_day') }}

select * from {{ ref('daily_aggregates') }}
{% if is_incremental() %}
    where date_day >= dateadd(day, -3, current_date())
{% endif %}
```

---

## Memory Integration

### Before Implementing Incrementals

Query the memory system for relevant patterns:

1. **Check past implementations**: `.claude/memory/patterns/successful-optimizations.json`
   - "What incremental strategies have worked for similar tables?"
   - "What lookback windows have we used for late-arriving data?"

2. **Check failure patterns**: `.claude/memory/patterns/common-test-failures.json`
   - "What incremental issues have caused test failures before?"

### Project Heuristics

Based on this project's data:

| Table Size | Recommendation |
|------------|----------------|
| < 10M rows | Start with `table` materialization |
| 10M-100M rows | Consider incremental with `merge` |
| > 100M rows | Use incremental (required) |

**Check table sizes via MCP:**
```sql
-- Use mcp__snowflake__run_snowflake_query
SELECT table_name, row_count
FROM information_schema.tables
WHERE table_schema = 'ANALYTICS'
ORDER BY row_count DESC;
```

### After Implementation

Store learnings in memory:

1. **Record performance gains**: Update `.claude/memory/baselines/model-build-times.json`
2. **Document strategy choice**: Note which strategy worked and why
3. **Track issues**: If problems occur, add to patterns for future reference

### Common Patterns from This Project

**Activity Tables (`act_*`)**: Always use `append` strategy
- Immutable events, never update
- Example: `act_transaction_posted` uses append

**Entity Tables (`fct_*`, `dim_*`)**: Use `merge` strategy
- Records can be updated
- Example: `fct_subscriptions` uses merge with `updated_at`

**Net Tables (`net_*`)**: Use `delete+insert` strategy
- Period-based aggregations
- Example: `net_mrr_metrics` uses delete+insert on `date_month`