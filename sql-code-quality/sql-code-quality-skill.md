---
name: sql-code-quality
description: SQL code quality standards, patterns, and best practices for dbt projects. Use when: "review this SQL", "is this good SQL", "SQL patterns", "SQL best practices", "how to write CTEs", "SQL formatting", "SQL style", "clean up this query", "optimize SQL", "SQL code review"
---

# SQL Code Quality Guide

Standards and patterns for writing high-quality SQL in dbt projects.

## SQL Formatting Standards

### Indentation & Whitespace
- Use 4 spaces for indentation (no tabs)
- One column per line in SELECT statements
- Blank lines between CTEs
- Align ON clauses in joins

### Case Conventions
- Lowercase for all SQL keywords (`select`, `from`, `where`, `join`)
- Lowercase for column and table names
- `snake_case` for all identifiers

### Commas
- Use trailing commas (comma at end of line)
- Makes diffs cleaner and reduces errors when reordering

```sql
-- Good: Trailing commas
select
    order_id,
    customer_id,
    order_date,
    order_amount,
from orders

-- Bad: Leading commas
select
    order_id
    , customer_id
    , order_date
    , order_amount
from orders
```

## CTE Pattern (Imports → Logic → Final)

Every model should follow this structure:

```sql
{{
    config(
        materialized='table'
    )
}}

with

-- ============================================
-- IMPORT CTEs (upstream dependencies)
-- ============================================
source_orders as (
    select * from {{ ref('stg_orders') }}
),

source_customers as (
    select * from {{ ref('stg_customers') }}
),

-- ============================================
-- LOGICAL CTEs (transformations)
-- ============================================
filtered_orders as (
    select
        order_id,
        customer_id,
        order_date,
        order_amount
    from source_orders
    where order_status != 'cancelled'
),

enriched_orders as (
    select
        o.order_id,
        o.customer_id,
        o.order_date,
        o.order_amount,
        c.customer_segment,
        c.customer_region
    from filtered_orders o
    left join source_customers c
        on o.customer_id = c.customer_id
),

-- ============================================
-- FINAL CTE (output)
-- ============================================
final as (
    select
        order_id,
        customer_id,
        customer_segment,
        customer_region,
        order_date,
        order_amount,
        current_timestamp() as _dbt_loaded_at
    from enriched_orders
)

select * from final
```

**Key Rules:**
- Config block at top
- Import CTEs first (just `select *` from refs)
- Logical CTEs in middle (transformations)
- Final CTE for output
- End with `select * from final`

## Column Naming Conventions

### Standard Suffixes
| Suffix | Usage | Example |
|--------|-------|---------|
| `_id` | Primary/foreign keys | `customer_id`, `order_id` |
| `_at` | Timestamps | `created_at`, `updated_at` |
| `_date` | Date only (no time) | `order_date`, `birth_date` |
| `_name` | Names/labels | `customer_name`, `product_name` |
| `_amount` | Money values | `order_amount`, `discount_amount` |
| `_count` | Counts | `order_count`, `line_item_count` |
| `_flag` or `is_` | Booleans | `is_active`, `has_subscription` |

### Naming Guidelines
- Be descriptive (no abbreviations except industry standard)
- Prefix foreign keys with source entity: `customer_id`, not just `id`
- Use full words: `customer_segment`, not `cust_seg`
- Boolean columns start with `is_` or `has_`

## Safe Division Pattern

**Always protect against divide-by-zero:**

```sql
-- Good: Safe division with NULLIF
sum(revenue) / nullif(count(distinct customer_id), 0) as revenue_per_customer

-- Bad: Can fail with division by zero
sum(revenue) / count(distinct customer_id) as revenue_per_customer
```

**Pattern for ratios and percentages:**
```sql
-- Conversion rate (safe)
count(distinct converted_user_id) / nullif(count(distinct user_id), 0) as conversion_rate

-- Percentage (safe, multiply by 100)
count(distinct churned_customers) / nullif(count(distinct total_customers), 0) * 100 as churn_percentage
```

## Null Handling Patterns

```sql
-- Coalesce for default values
coalesce(discount_amount, 0) as discount_amount

-- NULLIF to convert empty strings to NULL
nullif(trim(customer_name), '') as customer_name

-- Handle NULLs in comparisons
where customer_segment is not null
  and customer_segment != ''

-- Safe string concatenation
coalesce(first_name, '') || ' ' || coalesce(last_name, '') as full_name
```

## Window Function Patterns

### Row Numbering
```sql
-- Get latest record per customer
select *
from orders
qualify row_number() over (
    partition by customer_id
    order by order_date desc
) = 1
```

### Running Totals
```sql
sum(order_amount) over (
    partition by customer_id
    order by order_date
    rows between unbounded preceding and current row
) as cumulative_spend
```

### Lead/Lag
```sql
-- Previous order date
lag(order_date) over (
    partition by customer_id
    order by order_date
) as previous_order_date

-- Days since last order
datediff('day',
    lag(order_date) over (partition by customer_id order by order_date),
    order_date
) as days_since_last_order
```

### Ranking
```sql
-- Dense rank for ties
dense_rank() over (
    partition by category
    order by total_sales desc
) as sales_rank
```

## Join Patterns

### Explicit Join Syntax
```sql
-- Good: Explicit ANSI joins
select
    o.order_id,
    c.customer_name
from orders o
left join customers c
    on o.customer_id = c.customer_id

-- Bad: Implicit joins (comma syntax)
select
    o.order_id,
    c.customer_name
from orders o, customers c
where o.customer_id = c.customer_id
```

### Join Order for Performance
```sql
-- Good: Filter before joining
with filtered_orders as (
    select *
    from orders
    where order_date >= '2024-01-01'
)

select *
from filtered_orders o
left join customers c on o.customer_id = c.customer_id

-- Less efficient: Filter after joining
select *
from orders o
left join customers c on o.customer_id = c.customer_id
where o.order_date >= '2024-01-01'
```

### Multiple Join Conditions
```sql
-- Align ON conditions
left join dim_date d
    on o.order_date = d.date_day
    and o.fiscal_year = d.fiscal_year
```

## Aggregation Patterns

### Pre-filter Before Aggregating
```sql
-- Good: Filter first
select
    customer_segment,
    sum(order_amount) as total_revenue
from orders
where order_date >= '2024-01-01'
  and order_status = 'completed'
group by 1

-- Less efficient: Filter after
select *
from (
    select
        customer_segment,
        sum(order_amount) as total_revenue
    from orders
    group by 1
)
where total_revenue > 1000
```

### Use HAVING for Aggregate Filters
```sql
select
    customer_id,
    count(*) as order_count,
    sum(order_amount) as total_spend
from orders
group by 1
having count(*) >= 5  -- Use HAVING for aggregate conditions
```

## Common SQL Patterns

### Surrogate Keys
```sql
{{ dbt_utils.generate_surrogate_key(['order_id', 'line_item_number']) }} as order_line_id
```

### Date Truncation
```sql
date_trunc('month', order_date)::date as order_month
date_trunc('week', order_date)::date as order_week
```

### Conditional Aggregation
```sql
sum(case when order_status = 'completed' then order_amount else 0 end) as completed_revenue,
sum(case when order_status = 'cancelled' then order_amount else 0 end) as cancelled_revenue
```

### CASE Statements
```sql
-- Simple case
case order_status
    when 'pending' then 'Pending'
    when 'shipped' then 'Shipped'
    else 'Unknown'
end as status_label

-- Searched case (with conditions)
case
    when order_amount >= 1000 then 'large'
    when order_amount >= 100 then 'medium'
    else 'small'
end as order_size
```

### Union Pattern
```sql
with combined as (
    select *, 'shopify' as source_system from {{ ref('stg_shopify__orders') }}
    union all
    select *, 'amazon' as source_system from {{ ref('stg_amazon__orders') }}
)
```

## SQL Anti-Patterns to Avoid

### 1. SELECT * in Production Models
```sql
-- Bad: SELECT * hides schema changes
select * from orders

-- Good: Explicit columns
select
    order_id,
    customer_id,
    order_date,
    order_amount
from orders
```

### 2. Division Without Protection
```sql
-- Bad: Can fail
revenue / customers as arpu

-- Good: Protected
revenue / nullif(customers, 0) as arpu
```

### 3. Implicit Type Conversions
```sql
-- Bad: Implicit conversion
where order_date = '2024-01-01'

-- Good: Explicit conversion
where order_date = '2024-01-01'::date
```

### 4. NOT IN with NULLs
```sql
-- Bad: NOT IN behaves unexpectedly with NULLs
where customer_id not in (select customer_id from excluded_customers)

-- Good: Use NOT EXISTS or LEFT JOIN
where not exists (
    select 1 from excluded_customers e
    where e.customer_id = customers.customer_id
)
```

### 5. Correlated Subqueries in SELECT
```sql
-- Bad: Runs subquery for each row
select
    order_id,
    (select max(order_date) from orders o2 where o2.customer_id = o1.customer_id) as latest_order
from orders o1

-- Good: Use window function
select
    order_id,
    max(order_date) over (partition by customer_id) as latest_order
from orders
```

### 6. DISTINCT as a Band-Aid
```sql
-- Bad: Using DISTINCT to hide duplicate issues
select distinct customer_id, customer_name from customers

-- Good: Fix the root cause (proper joins, deduplication logic)
select customer_id, customer_name
from customers
qualify row_number() over (partition by customer_id order by updated_at desc) = 1
```

## Code Quality Checklist

Before committing any SQL model:

- [ ] Follows CTE pattern (imports → logic → final)
- [ ] Config block at top
- [ ] Lowercase keywords
- [ ] 4-space indentation
- [ ] Trailing commas
- [ ] No `SELECT *` except in import CTEs
- [ ] Safe division with `nullif()`
- [ ] Explicit column names
- [ ] Descriptive CTE names
- [ ] Comments for complex logic
- [ ] Proper use of `{{ ref() }}` and `{{ source() }}`
- [ ] No hardcoded values (use variables)
- [ ] Appropriate data types
- [ ] Null handling addressed

## Quick Reference

### Snowflake-Specific Patterns

**QUALIFY (filter window functions):**
```sql
select *
from orders
qualify row_number() over (partition by customer_id order by order_date desc) = 1
```

**FLATTEN (JSON/arrays):**
```sql
select
    value:id::string as item_id,
    value:name::string as item_name
from orders,
lateral flatten(input => line_items)
```

**TRY_CAST (safe casting):**
```sql
try_cast(value as integer) as numeric_value
```

**IFF (simple conditional):**
```sql
iff(is_active, 'Active', 'Inactive') as status_label
```

---

## Memory Integration

### Before Writing SQL

Check for project-specific patterns:

1. **Review past code reviews**: `.claude/memory/reflections/reviews/`
   - "What SQL patterns have been flagged in reviews?"
   - "What style issues come up repeatedly?"

2. **Check common issues**: `.claude/memory/patterns/common-test-failures.json`
   - Issues often trace back to SQL patterns

### Project SQL Conventions

Based on this project's established patterns:

#### Import CTE Naming
```sql
-- Use source_ prefix for raw imports
source_orders as (select * from {{ ref('stg_orders') }}),
source_customers as (select * from {{ ref('stg_customers') }}),

-- Use descriptive names for logic CTEs
filtered_orders as (...),
enriched_orders as (...),
aggregated_metrics as (...),

-- Always end with final
final as (...)
```

#### Safe Division in This Project
```sql
-- Standard pattern used across all metrics
sum(revenue) / nullif(count(distinct customer_id), 0) as arpu

-- For percentages (always multiply by 100 AFTER division)
count(churned) / nullif(count(*), 0) * 100 as churn_rate
```

#### Standard Metadata Columns
```sql
-- Always include at end of SELECT
current_timestamp() as _dbt_loaded_at
```

### SQLFluff Integration

Before committing, run linting:

```bash
# Lint SQL files
sqlfluff lint models/

# Auto-fix simple issues
sqlfluff fix models/ --force
```

### After Writing SQL

Self-check against quality checklist:

```markdown
## SQL Quality Self-Check

- [ ] CTE pattern: imports → logic → final
- [ ] All divisions protected with NULLIF
- [ ] No SELECT * except in import CTEs
- [ ] Trailing commas used
- [ ] Lowercase keywords
- [ ] 4-space indentation
- [ ] Descriptive CTE names
- [ ] _dbt_loaded_at included
```

If issues found during review, update `.claude/memory/patterns/` with the pattern to avoid.