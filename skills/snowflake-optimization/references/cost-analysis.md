# Cost Analysis & Optimization

Comprehensive guide to monitoring and reducing Snowflake costs.

## Cost Structure

Snowflake costs come from three main areas:

1. **Compute** (Warehouse usage) - ~70% of typical costs
2. **Storage** (Data + Time Travel + Fail-safe) - ~25%
3. **Cloud Services** (Metadata, query compilation) - ~5%

## Compute Cost Optimization

### 1. Right-Size Warehouses

See [warehouse-sizing.md](warehouse-sizing.md) for detailed guidance.

**Quick wins:**
- ❌ Don't use X-Large when Medium works
- ✅ Match warehouse size to workload
- ✅ Use separate warehouses for different workloads

### 2. Enable Auto-Suspend

```sql
ALTER WAREHOUSE analytics_wh SET
    auto_suspend = 60        -- 1 minute
    auto_resume = true;
```

**Impact**: 50-80% reduction in idle compute costs.

**Recommended settings**:
- Development: 60 seconds
- ETL/dbt: 60 seconds
- BI Dashboards: 300 seconds
- Production API: 300-600 seconds

### 3. Workload Separation

Create dedicated warehouses:

```
ETL_WH        → dbt builds
ANALYTICS_WH  → analyst queries
DASHBOARD_WH  → BI tools
DEV_WH        → development
```

**Benefits**:
- Prevent contention
- Clear cost attribution
- Appropriate sizing per workload
- Better cost control

### 4. Resource Monitors

Set spending limits:

```sql
CREATE RESOURCE MONITOR monthly_limit
    WITH CREDIT_QUOTA = 1000
    TRIGGERS
        ON 75 PERCENT DO NOTIFY
        ON 90 PERCENT DO NOTIFY
        ON 100 PERCENT DO SUSPEND;

ALTER WAREHOUSE analytics_wh SET RESOURCE_MONITOR = monthly_limit;
```

## Storage Cost Optimization

### 1. Use Transient Tables

```sql
-- In dbt
{{
    config(
        materialized='table',
        transient=true  -- 50% storage cost savings
    )
}}
```

**When to use**:
- Staging models
- Intermediate transformations
- Temporary results
- Data you can recreate

**When NOT to use**:
- Final reporting tables
- Critical business data
- Data requiring 7+ days Time Travel

### 2. Minimize Time Travel Retention

```sql
-- Production (keep default 1 day)
ALTER TABLE prod.fact_orders
SET DATA_RETENTION_TIME_IN_DAYS = 1;

-- Development (can set to 0)
ALTER TABLE dev.staging_orders
SET DATA_RETENTION_TIME_IN_DAYS = 0;
```

| Environment | Retention | Rationale |
|-------------|-----------|-----------|
| Production | 1-7 days | Balance recovery vs cost |
| Staging | 1 day | Limited need for recovery |
| Development | 0 days | Recreatable data |

### 3. Drop Unused Tables

```sql
-- Find large unused tables
SELECT
    table_catalog,
    table_schema,
    table_name,
    bytes / 1e9 AS gb_storage,
    row_count
FROM snowflake.account_usage.table_storage_metrics
WHERE bytes > 1e9  -- > 1GB
    AND table_name NOT IN (
        SELECT DISTINCT table_name
        FROM snowflake.account_usage.access_history
        WHERE query_start_time >= DATEADD(month, -3, CURRENT_TIMESTAMP())
    )
ORDER BY bytes DESC;
```

### 4. Optimize Cloning Usage

```sql
-- Use ZERO_COPY_CLONE for testing
CREATE TABLE dev.test_table CLONE prod.fact_orders;

-- This shares storage until modified
-- But Time Travel applies to both tables
```

**Cost consideration**: Clones share storage initially but diverge over time.

## Query Cost Optimization

### 1. Avoid Full Table Scans

**Problem**: Scanning entire tables is expensive.

**Solutions**:
- Add clustering keys (see [clustering-strategies.md](clustering-strategies.md))
- Add WHERE clauses with date filters
- Use incremental models in dbt

### 2. Select Only Needed Columns

```sql
-- ❌ Expensive
SELECT * FROM large_table;

-- ✅ Optimized
SELECT id, name, date FROM large_table;
```

**Impact**: 20-80% cost reduction depending on table width.

### 3. Leverage Result Caching

Snowflake caches identical queries for 24 hours (free):

- ✅ Identical queries = cached results
- ❌ Even slight differences = new query

**Pro tip**: Standardize date ranges in BI tools to maximize cache hits.

### 4. Schedule Large Jobs Off-Peak

If your contract has time-based pricing:
- Schedule heavy dbt builds for nights/weekends
- Run data science workloads during off-peak hours

## Cost Monitoring

### Track Daily Credit Usage

Use `scripts/cost-breakdown-query.sql`:

```sql
SELECT
    DATE_TRUNC('day', start_time) AS day,
    warehouse_name,
    SUM(credits_used) AS total_credits,
    SUM(credits_used) * 3 AS estimated_cost_usd
FROM snowflake.account_usage.warehouse_metering_history
WHERE start_time >= DATEADD(day, -30, CURRENT_TIMESTAMP())
GROUP BY 1, 2
ORDER BY 1 DESC, 3 DESC;
```

### Find Most Expensive Queries

```sql
SELECT
    query_text,
    user_name,
    warehouse_name,
    execution_time / 1000 AS duration_seconds,
    bytes_scanned / 1e9 AS gb_scanned,
    -- Estimate cost (adjust multiplier for your rate)
    (execution_time / 3600000.0) * warehouse_size_credits * 3 AS estimated_cost
FROM snowflake.account_usage.query_history
WHERE start_time >= DATEADD(day, -7, CURRENT_TIMESTAMP())
ORDER BY execution_time DESC
LIMIT 50;
```

### Storage Usage by Table

```sql
SELECT
    table_catalog,
    table_schema,
    table_name,
    bytes / 1e9 AS gb_storage,
    (bytes / 1e9) * 23 AS monthly_storage_cost_usd,  -- $23/TB/month
    row_count
FROM snowflake.account_usage.table_storage_metrics
WHERE bytes > 1e9  -- > 1GB
ORDER BY bytes DESC
LIMIT 20;
```

### Cost by Team/Workload

```sql
-- Assuming warehouse names indicate teams
SELECT
    warehouse_name,
    SUM(credits_used) AS total_credits,
    SUM(credits_used) * 3 AS estimated_cost_usd,
    COUNT(DISTINCT DATE_TRUNC('day', start_time)) AS days_active
FROM snowflake.account_usage.warehouse_metering_history
WHERE start_time >= DATEADD(month, -1, CURRENT_TIMESTAMP())
GROUP BY 1
ORDER BY 2 DESC;
```

## Cost Optimization Checklist

### Compute Costs ⚡
- [ ] Right-sized warehouses (not oversized)
- [ ] Auto-suspend enabled (60-120 seconds)
- [ ] Multi-cluster for variable workloads
- [ ] Separate warehouses by team/workload
- [ ] Resource monitors configured
- [ ] dbt thread count optimized

### Storage Costs 💾
- [ ] Transient tables for staging/intermediate
- [ ] Time Travel retention minimized (0-1 days for non-prod)
- [ ] Unused tables dropped
- [ ] Old data archived or deleted
- [ ] Cloning strategy documented

### Query Costs 🔍
- [ ] Large tables clustered
- [ ] SELECT * eliminated
- [ ] Incremental models for large tables
- [ ] Result caching leveraged
- [ ] Query patterns optimized

### Monitoring 📊
- [ ] Daily cost tracking automated
- [ ] Alerts for >20% cost increases
- [ ] Monthly cost review scheduled
- [ ] Cost attribution by team

## Common Cost Optimization Wins

From this analytics project:

| Optimization | Before | After | Savings |
|--------------|--------|-------|---------|
| Enable auto-suspend (60s) | Always on | Auto-suspend | 65% reduction |
| Right-size dev warehouse | Medium | X-Small | 75% reduction |
| Transient staging tables | Permanent | Transient | 50% storage cost |
| Add clustering to nets | Full scan | Pruned | 4x faster, 75% less compute |
| Incremental large facts | Full refresh | Incremental | 90% reduction |

## Advanced Cost Optimization

### dbt Incremental Strategy

```sql
{{
    config(
        materialized='incremental',
        unique_key='order_id',
        incremental_strategy='append',  -- Fastest, cheapest
        cluster_by=['order_date']
    )
}}

SELECT * FROM {{ ref('staging_orders') }}

{% if is_incremental() %}
    WHERE updated_at > (SELECT MAX(updated_at) FROM {{ this }})
{% endif %}
```

**Impact**: 5-10x cost reduction for large tables.

### Partition-Based Optimization

For time-series data:

```sql
{{
    config(
        materialized='incremental',
        unique_key='date_month',
        incremental_strategy='delete+insert',
        cluster_by=['date_month']
    )
}}

-- Only reprocess last 3 months
SELECT * FROM {{ ref('source') }}

{% if is_incremental() %}
    WHERE date_month >= DATEADD(month, -3, CURRENT_DATE())
{% endif %}
```

## Cost Alerting

Set up proactive alerts:

```sql
-- Create alert for unusual spending
CREATE ALERT high_daily_cost
    WAREHOUSE = analytics_wh
    SCHEDULE = 'USING CRON 0 9 * * * America/New_York'  -- 9 AM daily
AS
SELECT
    DATE_TRUNC('day', start_time) AS day,
    SUM(credits_used) AS daily_credits
FROM snowflake.account_usage.warehouse_metering_history
WHERE start_time >= DATEADD(day, -1, CURRENT_TIMESTAMP())
GROUP BY 1
HAVING SUM(credits_used) > 100;  -- Adjust threshold
```

## ROI Calculation Framework

When evaluating optimizations:

**Cost of Optimization** = Engineering time + testing + risk

**Benefit** = Monthly savings × 12 months

**Example**:
- Optimization: Add clustering to 5 large tables
- Engineering time: 4 hours
- Monthly savings: $200
- Annual ROI: ($200 × 12) / (4 hours × $150/hour) = 400% ROI

## Troubleshooting High Costs

### Symptom: Sudden cost spike

**Investigation steps**:
1. Check warehouse metering history
2. Identify which warehouse
3. Find expensive queries in that warehouse
4. Determine root cause (new workload, query regression, etc.)

### Symptom: Gradual cost increase

**Possible causes**:
1. Data volume growth (expected)
2. Increased user activity (good)
3. Query performance degradation (investigate)
4. Warehouses not suspending (check config)

### Symptom: Storage costs increasing

**Check**:
1. Table storage metrics (which tables growing?)
2. Time Travel retention settings
3. Cloned tables not being cleaned up
4. Fail-safe storage (look for dropped tables)

## Cost Optimization Resources

- **Snowflake Cost Calculator**: Estimate before implementing
- **Account Usage Views**: `WAREHOUSE_METERING_HISTORY`, `QUERY_HISTORY`, `TABLE_STORAGE_METRICS`
- **Resource Monitors**: Set up spending limits
- **SnowSight Cost Dashboard**: Built-in visualization (Admin > Account > Cost Management)
