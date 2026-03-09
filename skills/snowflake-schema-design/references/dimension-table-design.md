# Dimension Table Design Patterns

Comprehensive guide to designing dimension tables in Snowflake.

## Dimension Table Fundamentals

**What is a Dimension Table?**
- Contains descriptive attributes about business entities
- Provides context for facts
- Typically smaller than fact tables
- Examples: `dim_customers`, `dim_products`, `dim_dates`

**Key Components:**
- **Primary Key** (surrogate or natural)
- **Natural Key** (business identifier)
- **Attributes** (descriptive fields)
- **Hierarchies** (drilldown paths)
- **Derived Attributes** (calculated classifications)

---

## Dimension Table Template

```sql
{{
    config(
        materialized='table'
    )
}}

with

customers as (
    select * from {{ ref('stg_customers') }}
),

customer_orders as (
    select
        customer_id,
        min(order_date) as first_order_date,
        max(order_date) as last_order_date,
        count(*) as lifetime_orders,
        sum(order_amount) as lifetime_value
    from {{ ref('stg_orders') }}
    group by 1
),

final as (
    select
        -- Surrogate key
        {{ dbt_utils.generate_surrogate_key(['customer_id']) }} as customer_sk,

        -- Natural key
        c.customer_id,

        -- Attributes
        c.customer_name,
        c.customer_email,
        c.customer_phone,

        -- Hierarchies
        c.customer_segment,
        c.customer_tier,
        c.region,
        c.country,
        c.state,
        c.city,

        -- Dates
        c.created_at as customer_created_at,
        o.first_order_date,
        o.last_order_date,

        -- Derived metrics (denormalized for performance)
        o.lifetime_orders,
        o.lifetime_value,

        -- Derived attributes
        case
            when o.lifetime_value >= 10000 then 'platinum'
            when o.lifetime_value >= 5000 then 'gold'
            when o.lifetime_value >= 1000 then 'silver'
            else 'bronze'
        end as value_tier,

        -- Status flags
        c.is_active,
        coalesce(o.lifetime_orders, 0) > 0 as has_orders,

        -- Metadata
        current_timestamp() as _dbt_loaded_at

    from customers c
    left join customer_orders o on c.customer_id = o.customer_id
)

select * from final
```

---

## Common Dimension Patterns

### 1. Date Dimension

**Use Case:** Time intelligence queries

```sql
-- dim_date.sql
with date_spine as (
    {{ dbt_utils.date_spine(
        datepart="day",
        start_date="cast('2020-01-01' as date)",
        end_date="dateadd(year, 5, current_date())"
    ) }}
),

final as (
    select
        date_day,
        date_day as date_key,

        -- Date parts
        extract(year from date_day) as year,
        extract(quarter from date_day) as quarter,
        extract(month from date_day) as month,
        extract(week from date_day) as week_of_year,
        extract(dayofweek from date_day) as day_of_week,

        -- Formatted
        to_char(date_day, 'YYYY-MM') as year_month,
        to_char(date_day, 'Month') as month_name,
        to_char(date_day, 'Day') as day_name,

        -- Flags
        case when extract(dayofweek from date_day) in (0, 6) then true else false end as is_weekend,

        -- Fiscal (adjust as needed)
        case when extract(month from date_day) >= 2
             then extract(year from date_day)
             else extract(year from date_day) - 1
        end as fiscal_year,

        -- Relative periods
        current_date() - date_day as days_ago,
        case when date_day = current_date() then true else false end as is_today,
        case when date_day >= dateadd(day, -7, current_date()) then true else false end as is_last_7_days,
        case when date_day >= dateadd(day, -30, current_date()) then true else false end as is_last_30_days

    from date_spine
)

select * from final
```

**Benefits:**
- Pre-compute date calculations
- Standard date hierarchies
- Relative date flags (last 7 days, etc.)
- Fiscal calendar support

---

### 2. Bridge Table (Many-to-Many)

**Use Case:** Resolve many-to-many relationships

**Example:** One customer can have multiple accounts, one account can have multiple customers

```sql
-- bridge_customer_accounts.sql

{{
    config(
        materialized='table'
    )
}}

select
    {{ dbt_utils.generate_surrogate_key(['customer_id', 'account_id']) }} as bridge_sk,
    customer_id,
    account_id,
    relationship_type,  -- 'primary', 'secondary', 'authorized'
    start_date,
    end_date,
    is_current
from {{ ref('stg_customer_account_relationships') }}
```

**Query Pattern:**
```sql
-- Find all accounts for a customer
select
    c.customer_name,
    a.account_number,
    b.relationship_type
from dim_customers c
join bridge_customer_accounts b on c.customer_id = b.customer_id
join dim_accounts a on b.account_id = a.account_id
where b.is_current = true
```

---

### 3. Junk Dimension

**Use Case:** Consolidate low-cardinality flags into single dimension

**Example:** Order flags

```sql
-- dim_order_flags.sql
-- Consolidate low-cardinality flags

{{
    config(
        materialized='table'
    )
}}

select distinct
    {{ dbt_utils.generate_surrogate_key([
        'is_gift',
        'is_subscription',
        'is_bulk_order',
        'payment_method_type'
    ]) }} as order_flags_sk,
    is_gift,
    is_subscription,
    is_bulk_order,
    payment_method_type
from {{ ref('stg_orders') }}
```

**Benefits:**
- Reduces fact table width
- Combines related flags
- Easier to manage than individual columns

---

### 4. Role-Playing Dimension

**Use Case:** Same dimension used in multiple contexts

**Example:** Date dimension used for order_date, ship_date, delivery_date

```sql
-- fct_orders.sql
select
    order_id,
    order_date,     -- FK to dim_date
    ship_date,      -- FK to dim_date
    delivery_date   -- FK to dim_date
from {{ ref('stg_orders') }}
```

**Query Pattern:**
```sql
-- Join same dimension multiple times
select
    o.order_id,
    od.month_name as order_month,
    sd.month_name as ship_month,
    dd.month_name as delivery_month
from fct_orders o
left join dim_date od on o.order_date = od.date_day
left join dim_date sd on o.ship_date = sd.date_day
left join dim_date dd on o.delivery_date = dd.date_day
```

---

### 5. Conformed Dimension

**Use Case:** Shared dimension across multiple fact tables

**Example:** Customer dimension used by orders, subscriptions, support tickets

```sql
-- dim_customers.sql - shared across multiple marts

select
    customer_id,
    customer_name,
    customer_segment
from {{ ref('stg_customers') }}
```

**Benefits:**
- Consistent customer definitions across business processes
- Cross-process reporting (e.g., orders + support tickets)
- Single source of truth

---

## Dimension Design Best Practices

### 1. Use Surrogate Keys

**When to use surrogate keys:**
- Slowly Changing Dimensions (SCD Type 2)
- Natural key is composite or large
- Natural key can change over time

```sql
-- Generate surrogate key
{{ dbt_utils.generate_surrogate_key(['customer_id']) }} as customer_sk
```

### 2. Include Natural Key

Always keep the natural key even when using surrogate keys:

```sql
select
    customer_sk,      -- Surrogate key (for joins)
    customer_id,      -- Natural key (for business users)
    customer_name
from {{ ref('stg_customers') }}
```

### 3. Build Hierarchies

Support drilldown analysis with hierarchical attributes:

```sql
select
    product_id,
    product_name,
    -- Hierarchy: Category > Subcategory > Product
    product_category,
    product_subcategory,
    product_brand
from {{ ref('stg_products') }}
```

### 4. Add Derived Attributes

Pre-calculate common classifications:

```sql
select
    customer_id,
    lifetime_value,
    -- Derived attribute
    case
        when lifetime_value >= 10000 then 'platinum'
        when lifetime_value >= 5000 then 'gold'
        when lifetime_value >= 1000 then 'silver'
        else 'bronze'
    end as value_tier
from {{ ref('stg_customers') }}
```

### 5. Use Boolean Flags

Add flags for common filters:

```sql
select
    customer_id,
    customer_name,
    is_active,
    has_subscription,
    is_premium_member
from {{ ref('stg_customers') }}
```

---

## Handling Missing Dimension Records

### Option 1: Default "Unknown" Record

```sql
-- Create default record for missing dimensions
select
    -1 as customer_sk,
    'UNKNOWN' as customer_id,
    'Unknown Customer' as customer_name,
    'Unknown' as customer_segment

union all

select
    customer_sk,
    customer_id,
    customer_name,
    customer_segment
from {{ ref('stg_customers') }}
```

### Option 2: LEFT JOIN with COALESCE

```sql
-- Handle missing dimension gracefully
select
    f.order_id,
    f.customer_id,
    coalesce(c.customer_name, 'Unknown') as customer_name,
    coalesce(c.customer_segment, 'Unknown') as customer_segment
from fct_orders f
left join dim_customers c on f.customer_id = c.customer_id
```

---

## Testing Dimension Tables

```yaml
models:
  - name: dim_customers
    columns:
      - name: customer_sk
        tests:
          - unique
          - not_null
      - name: customer_id
        tests:
          - unique
          - not_null
      - name: customer_name
        tests:
          - not_null
      - name: customer_segment
        tests:
          - accepted_values:
              values: ['enterprise', 'mid-market', 'smb']
      - name: is_active
        tests:
          - not_null
          - accepted_values:
              values: [true, false]
```

---

## Dimension Table Anti-Patterns

### ❌ Massive Wide Dimensions

**Problem:** 100+ columns in one dimension

```sql
-- Bad: Too many columns
select * from dim_customers  -- 150 columns
```

**Solution:** Split into multiple dimensions or extract rarely-used attributes

### ❌ Missing Hierarchies

**Problem:** Can't drill down

```sql
-- Bad: No hierarchy
select product_name from dim_products
```

**Solution:** Add category, subcategory, brand levels

### ❌ Changing Natural Keys

**Problem:** Natural key changes, breaks joins

```sql
-- Bad: customer_id changes over time
update dim_customers set customer_id = 'NEW_ID' where customer_id = 'OLD_ID'
```

**Solution:** Use surrogate keys, keep natural key stable or use SCD Type 2

### ❌ No Unknown Record

**Problem:** Orphan facts with no dimension record

```sql
-- Bad: NULL values when dimension missing
select * from fct_orders o
left join dim_customers c on o.customer_id = c.customer_id
-- c.customer_name is NULL for missing customers
```

**Solution:** Add default "Unknown" record to dimension

---

## Performance Optimization

### Clustering for Large Dimensions

For large dimensions (> 10M rows), add clustering:

```sql
{{
    config(
        cluster_by=['customer_segment', 'region']
    )
}}
```

### Denormalize into Facts

For frequently-used attributes, denormalize into fact table:

```sql
-- Instead of joining dimension every time:
select
    order_id,
    customer_id,
    customer_segment,  -- Denormalized from dim_customers
    customer_region    -- Denormalized from dim_customers
from fct_orders
```

### Materialization Strategy

- **Small dimensions** (< 1M rows): Use `table` materialization
- **Large dimensions** (> 1M rows): Consider `incremental` for SCD Type 2
- **Static dimensions** (date, product types): Can be views if small

---

## Special Dimension Types

### Degenerate Dimension

Dimension attribute stored in fact table (no separate dimension):

```sql
-- order_number is a degenerate dimension in fct_orders
select
    order_id,
    order_number,  -- Degenerate dimension
    customer_id,   -- FK to dim_customers
    order_amount
from fct_orders
```

**When to use:** Unique identifiers or very low-cardinality attributes

### Mini-Dimension

Small dimension for frequently-changing attributes:

```sql
-- dim_customer_demographics.sql
-- Split fast-changing demographics from main customer dim

select
    customer_demographics_sk,
    age_range,
    income_bracket,
    marital_status,
    household_size
from {{ ref('stg_customer_demographics') }}
```

**Benefits:** Avoid explosion of SCD Type 2 rows in main dimension

### Outrigger Dimension

Dimension that references another dimension:

```sql
-- dim_products.sql references dim_product_categories

select
    product_id,
    product_name,
    category_id,  -- FK to dim_product_categories (outrigger)
    brand
from {{ ref('stg_products') }}
```

**Note:** Can impact query simplicity, use sparingly
