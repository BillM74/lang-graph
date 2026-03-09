# Clustering Strategies

Comprehensive guide to clustering keys in Snowflake.

## When to Cluster

Cluster tables that meet these criteria:
- **Data size**: > 1TB of data
- **Query patterns**: Frequently filtered on specific columns
- **Performance issues**: Queries show poor partition pruning

## Choosing Clustering Keys

### Selection Criteria

Good clustering key candidates (in priority order):
1. **Date columns** - Most common filter, almost always a good choice
2. **High-cardinality categorical columns** - Customer segment, product category
3. **Columns frequently in WHERE clauses** - Status, type, region

### Rules & Constraints

- **Maximum**: 3-4 columns per clustering key
- **Order matters**: Put most selective column first (usually date)
- **Avoid**: Columns that change frequently (will cause constant reclustering)
- **Consider**: Query patterns - what filters are users actually using?

### Examples

```sql
-- Good: Date + high-cardinality category
ALTER TABLE schema.fact_orders
CLUSTER BY (order_date, customer_segment);

-- Good: Date only for time-series data
ALTER TABLE schema.activity_pageviews
CLUSTER BY (event_timestamp);

-- Less optimal: Too many columns
ALTER TABLE schema.fact_orders
CLUSTER BY (order_date, customer_segment, product_category, order_status, region);
-- This will be expensive to maintain

-- Bad: Low-cardinality column only
ALTER TABLE schema.fact_orders
CLUSTER BY (order_status);  -- Only 3-5 values
```

## dbt Configuration

### Basic Clustering

```sql
{{
    config(
        materialized='table',
        cluster_by=['date_month', 'customer_segment']
    )
}}

SELECT ...
```

### Incremental with Clustering

```sql
{{
    config(
        materialized='incremental',
        unique_key='order_id',
        cluster_by=['order_date', 'customer_segment'],
        incremental_strategy='merge'
    )
}}

SELECT ...
```

## Monitoring Clustering Health

### Check Clustering Depth

Lower depth is better (1-2 is ideal):

```sql
-- Quick depth check
SELECT SYSTEM$CLUSTERING_DEPTH('schema.table_name');

-- Detailed clustering information
SELECT SYSTEM$CLUSTERING_INFORMATION('schema.table_name');
```

### Find Tables Needing Reclustering

Use the `clustering-health-check.sql` script from `scripts/`:

```sql
SELECT
    table_name,
    clustering_key,
    average_depth,
    average_overlaps
FROM snowflake.account_usage.tables
WHERE table_schema = 'ANALYTICS'
    AND average_depth > 4;  -- Needs attention if > 4
```

### Clustering Health Thresholds

| Average Depth | Status | Action |
|---------------|--------|--------|
| 1-2 | 🟢 Healthy | No action needed |
| 3-4 | 🟡 Monitor | Watch for degradation |
| > 4 | 🔴 Needs Reclustering | Consider manual recluster or review key choice |

## Manual Reclustering

If automatic maintenance isn't keeping up:

```sql
-- Force recluster
ALTER TABLE schema.table_name RECLUSTER;

-- Check progress
SELECT SYSTEM$CLUSTERING_INFORMATION('schema.table_name');
```

**Note**: Reclustering consumes credits. Only manually recluster if automatic maintenance isn't sufficient.

## Clustering vs Partitioning

| Feature | Snowflake Clustering | Traditional Partitioning |
|---------|---------------------|-------------------------|
| Maintenance | Automatic | Manual |
| Key changes | Can be altered | Usually fixed |
| Overhead | Low (micro-partitions) | High (managing partitions) |
| Best for | Large tables, varied queries | Append-only, time-series |

## Common Patterns from This Project

Based on successful clusterings in this analytics project:

| Table Type | Typical Clustering Key | Improvement |
|------------|----------------------|-------------|
| Fact tables | `(order_date, customer_segment)` | 3-5x faster |
| Activity streams | `(event_timestamp)` | 4-6x faster |
| Dimension tables | Usually not needed (< 1TB) | N/A |
| Nets (reporting) | `(date_month, metric_category)` | 2-4x faster |

## Troubleshooting

### Problem: Clustering key not improving performance

**Possible causes:**
1. Queries don't filter on clustered columns
2. Key order doesn't match query patterns
3. Table too small to benefit (< 1TB)
4. Too many clustering keys

**Solution**: Review actual query patterns and adjust key accordingly.

### Problem: Constant reclustering costs

**Possible causes:**
1. Clustered on frequently changing columns
2. Too many columns in key
3. Incremental model with poor merge strategy

**Solution**: Rethink clustering key or switch to simpler key (date only).

### Problem: Average depth keeps increasing

**Possible causes:**
1. High volume of updates/deletes
2. Automatic clustering suspended
3. Key doesn't align with data distribution

**Solution**: Check ACCOUNT_USAGE.AUTOMATIC_CLUSTERING_HISTORY for maintenance activity.
