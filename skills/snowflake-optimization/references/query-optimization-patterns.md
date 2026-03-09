# Query Optimization Patterns

SQL patterns and anti-patterns for Snowflake query optimization.

## Core Optimization Principles

1. **Filter early** - Reduce data before operations
2. **Select specific columns** - Avoid SELECT *
3. **Use QUALIFY** - Efficient window function filtering
4. **Pre-aggregate** - Reduce before joining
5. **Leverage clustering** - Design queries to use clustered columns

## Pattern 1: Avoid SELECT *

### ❌ Anti-Pattern
```sql
SELECT * FROM large_fact_table
WHERE order_date >= '2024-01-01';
```

**Problem**: Scans all columns, even if only need a few.

### ✅ Optimized
```sql
SELECT order_id, customer_id, order_date, amount
FROM large_fact_table
WHERE order_date >= '2024-01-01';
```

**Impact**: 20-80% reduction in bytes scanned (depending on table width).

## Pattern 2: Filter Before Joining

### ❌ Anti-Pattern
```sql
SELECT *
FROM fact_table a
JOIN dimension_table b ON a.customer_id = b.customer_id
WHERE a.order_date >= '2024-01-01'
    AND b.is_active = true;
```

**Problem**: Joins entire tables, then filters.

### ✅ Optimized
```sql
WITH
filtered_facts AS (
    SELECT *
    FROM fact_table
    WHERE order_date >= '2024-01-01'
),
filtered_dims AS (
    SELECT *
    FROM dimension_table
    WHERE is_active = true
)
SELECT
    f.order_id,
    f.order_amount,
    d.customer_segment
FROM filtered_facts f
LEFT JOIN filtered_dims d
    ON f.customer_id = d.customer_id;
```

**Impact**: 2-5x faster for large tables.

## Pattern 3: Use QUALIFY for Window Functions

### ❌ Anti-Pattern
```sql
SELECT *
FROM (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY customer_id
            ORDER BY order_date DESC
        ) AS rn
    FROM orders
)
WHERE rn = 1;
```

**Problem**: Materializes ROW_NUMBER column unnecessarily.

### ✅ Optimized
```sql
SELECT *
FROM orders
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY customer_id
    ORDER BY order_date DESC
) = 1;
```

**Impact**: 15-30% faster, cleaner SQL.

## Pattern 4: Efficient Window Functions

### ❌ Anti-Pattern
```sql
-- Unbounded window across millions of rows
SELECT
    *,
    ROW_NUMBER() OVER (ORDER BY transaction_date) AS rn
FROM millions_of_rows;
```

**Problem**: Single massive partition.

### ✅ Optimized
```sql
-- Partitioned windows with date filter
SELECT
    *,
    ROW_NUMBER() OVER (
        PARTITION BY customer_id
        ORDER BY transaction_date
    ) AS customer_transaction_seq
FROM millions_of_rows
WHERE transaction_date >= '2024-01-01';
```

**Impact**: 5-10x faster through partitioning and filtering.

## Pattern 5: Pre-Aggregate Before Joining

### ❌ Anti-Pattern
```sql
SELECT
    d.customer_segment,
    SUM(f.amount) AS total_amount
FROM
    fact_orders f
    JOIN dim_customers d ON f.customer_id = d.customer_id
WHERE f.order_date >= '2024-01-01'
GROUP BY 1;
```

**Problem**: Joins millions of rows, then aggregates.

### ✅ Optimized
```sql
WITH
order_totals AS (
    SELECT
        customer_id,
        SUM(amount) AS total_amount
    FROM fact_orders
    WHERE order_date >= '2024-01-01'
    GROUP BY 1
)
SELECT
    d.customer_segment,
    SUM(o.total_amount) AS total_amount
FROM order_totals o
JOIN dim_customers d ON o.customer_id = d.customer_id
GROUP BY 1;
```

**Impact**: 3-5x faster by reducing join size.

## Pattern 6: Use Transient Tables for Staging

### dbt Configuration
```sql
{{
    config(
        materialized='table',
        transient=true  -- No Fail-safe, 50% storage cost savings
    )
}}

SELECT ...
FROM {{ ref('staging_model') }}
```

**When to use**: Intermediate tables, staging models, temporary results.
**Impact**: 50% reduction in storage costs.

## Pattern 7: Optimize Aggregations

### ❌ Anti-Pattern
```sql
-- Filter after aggregation
SELECT customer_segment, total_amount
FROM (
    SELECT
        customer_segment,
        SUM(amount) AS total_amount
    FROM orders
    GROUP BY 1
)
WHERE total_amount > 1000;
```

### ✅ Optimized
```sql
-- Filter before aggregation when possible
SELECT
    customer_segment,
    SUM(amount) AS total_amount
FROM orders
WHERE order_date >= '2024-01-01'  -- Reduce data early
GROUP BY 1
HAVING SUM(amount) > 1000;  -- Post-aggregation filter
```

## Pattern 8: Leverage Clustering Keys

### ❌ Anti-Pattern
```sql
-- Query doesn't use clustering key
SELECT *
FROM clustered_table  -- Clustered on (order_date, customer_segment)
WHERE product_category = 'Electronics';
```

**Problem**: Full table scan despite clustering.

### ✅ Optimized
```sql
-- Query uses clustering key
SELECT *
FROM clustered_table  -- Clustered on (order_date, customer_segment)
WHERE order_date >= '2024-01-01'
    AND customer_segment = 'Enterprise';
```

**Impact**: 5-10x faster through partition pruning.

## Pattern 9: Avoid Cartesian Products

### ❌ Anti-Pattern
```sql
-- Missing join condition
SELECT *
FROM orders o, customers c
WHERE o.order_date >= '2024-01-01';
```

**Problem**: Cartesian product (every order × every customer).

### ✅ Optimized
```sql
SELECT *
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
WHERE o.order_date >= '2024-01-01';
```

## Pattern 10: Efficient CTEs

### CTE Ordering Best Practice

```sql
WITH
-- 1. Import CTEs (reference sources)
orders_source AS (
    SELECT * FROM {{ source('raw', 'orders') }}
),
customers_source AS (
    SELECT * FROM {{ source('raw', 'customers') }}
),

-- 2. Filter CTEs (reduce data early)
recent_orders AS (
    SELECT *
    FROM orders_source
    WHERE order_date >= '2024-01-01'
),
active_customers AS (
    SELECT *
    FROM customers_source
    WHERE is_active = true
),

-- 3. Logic CTEs (transformations)
enriched_orders AS (
    SELECT
        o.order_id,
        o.amount,
        c.customer_segment
    FROM recent_orders o
    LEFT JOIN active_customers c
        ON o.customer_id = c.customer_id
),

-- 4. Final CTE (output shape)
final AS (
    SELECT
        customer_segment,
        COUNT(*) AS order_count,
        SUM(amount) AS total_amount
    FROM enriched_orders
    GROUP BY 1
)

SELECT * FROM final
```

## Snowflake-Specific Optimizations

### FLATTEN for Variant Data

```sql
-- Efficient FLATTEN usage
SELECT
    raw_data:id::STRING AS id,
    value:name::STRING AS item_name,
    value:quantity::NUMBER AS quantity
FROM raw_table,
LATERAL FLATTEN(input => raw_data:items)
WHERE raw_data:order_date >= '2024-01-01';
```

### TRY_CAST for Safe Conversions

```sql
-- Use TRY_CAST to avoid query failures
SELECT
    order_id,
    TRY_CAST(amount_string AS NUMBER) AS amount,
    TRY_TO_DATE(date_string, 'YYYY-MM-DD') AS order_date
FROM staging_orders
WHERE TRY_CAST(amount_string AS NUMBER) IS NOT NULL;
```

### IFF for Conditional Logic

```sql
-- IFF is more concise than CASE
SELECT
    order_id,
    IFF(amount > 1000, 'Large', 'Small') AS order_size
FROM orders;
```

## Common Performance Anti-Patterns

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| SELECT * | Scans unnecessary columns | Select specific columns |
| No date filters | Full table scan | Add date range filter |
| Joins before filters | Large intermediate results | Filter in CTEs first |
| Unbounded windows | Single massive partition | Add PARTITION BY |
| Missing QUALIFY | Extra subquery layer | Use QUALIFY directly |
| Cartesian products | Exponential row explosion | Check join conditions |
| Post-aggregation filters | Aggregates unnecessary data | Pre-filter with WHERE |

## Query Profiling Checklist

Use `scripts/query-profile-analyzer.sql` to check:

- [ ] **Bytes scanned** - Should be proportional to data needed
- [ ] **Partition pruning** - `partitions_scanned` << `partitions_total`
- [ ] **Spillage** - Should be zero (check warehouse sizing)
- [ ] **Join explosion** - Rows out > rows in indicates fan-out
- [ ] **Query duration** - Compare to baseline expectations

## Project-Specific Patterns

From this analytics project:

| Pattern | Typical Impact | Use Case |
|---------|----------------|----------|
| Filter on `date_month` first | 5x faster | SOMA nets tables |
| Use QUALIFY for latest record | 2x faster | SCD Type 2 dimensions |
| Pre-filter before ref() | 3x faster | dbt models with large deps |
| Cluster by (`date_month`, `segment`) | 4x faster | Reporting tables |
