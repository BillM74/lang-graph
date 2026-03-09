# Fact Table Design Patterns

Comprehensive guide to designing fact tables in Snowflake.

## Fact Table Fundamentals

**What is a Fact Table?**
- Contains measurements/metrics at a specific grain
- Joined to dimension tables via foreign keys
- Typically the largest tables in the warehouse
- Examples: `fct_orders`, `fct_subscriptions`, `fct_payments`

**Key Components:**
- **Primary Key** (surrogate or natural)
- **Foreign Keys** to dimensions
- **Facts** (measurements, metrics, quantities)
- **Degenerate Dimensions** (dimension attributes without separate table)
- **Date Keys** (for time-based analysis)

---

## Fact Table Template

```sql
{{
    config(
        materialized='table',
        cluster_by=['order_date', 'customer_segment']
    )
}}

with

orders as (
    select * from {{ ref('stg_orders') }}
),

final as (
    select
        -- Surrogate key (optional but recommended)
        {{ dbt_utils.generate_surrogate_key(['order_id']) }} as order_sk,

        -- Natural key
        order_id,

        -- Foreign keys to dimensions
        customer_id,
        product_id,
        location_id,

        -- Degenerate dimensions (no separate dim table)
        order_number,
        invoice_number,

        -- Date keys
        order_date,
        ship_date,

        -- Facts (measurements)
        quantity,
        unit_price,
        discount_amount,
        tax_amount,
        order_amount,
        shipping_cost,

        -- Calculated facts
        order_amount - discount_amount as net_amount,
        order_amount + tax_amount + shipping_cost as total_amount,

        -- Denormalized dimensions (SOMA pattern)
        customer_segment,
        customer_region,
        product_category,

        -- Metadata
        current_timestamp() as _dbt_loaded_at

    from orders
)

select * from final
```

---

## Fact Table Types

### 1. Transaction Fact Tables

**Grain:** One row per transaction event

**Use Cases:**
- Order transactions
- Payment transactions
- Login events
- API calls

**Example:**
```sql
-- fct_orders.sql
-- Grain: One row per order

select
    order_id,
    customer_id,
    order_date,
    order_amount,
    order_quantity,
    order_status
from {{ ref('stg_orders') }}
```

**Characteristics:**
- Highly granular
- Immutable (records don't change after insert)
- Grows continuously
- Good candidate for incremental models

---

### 2. Periodic Snapshot Fact Tables

**Grain:** One row per period per entity

**Use Cases:**
- Daily account balances
- Monthly inventory levels
- Quarterly revenue snapshots

**Example:**
```sql
-- fct_account_balance_daily.sql
-- Grain: One row per account per day

select
    account_id,
    date_day,
    beginning_balance,
    ending_balance,
    deposits,
    withdrawals,
    interest_earned
from {{ ref('int_account_daily_activity') }}
```

**Characteristics:**
- Fixed grain (e.g., daily, monthly)
- Semi-additive facts (balances)
- Rows can be updated or overwritten
- Good for trending and period comparisons

---

### 3. Accumulating Snapshot Fact Tables

**Grain:** One row per process instance with multiple milestones

**Use Cases:**
- Order fulfillment pipeline
- Support ticket lifecycle
- Customer onboarding journey

**Example:**
```sql
-- fct_order_fulfillment.sql
-- Grain: One row per order, updated as order progresses

select
    order_id,
    customer_id,

    -- Milestone dates
    order_date,
    payment_confirmed_date,
    picked_date,
    packed_date,
    shipped_date,
    delivered_date,

    -- Lag metrics (calculated from milestones)
    datediff(day, order_date, payment_confirmed_date) as days_to_payment,
    datediff(day, payment_confirmed_date, shipped_date) as days_to_ship,
    datediff(day, shipped_date, delivered_date) as days_in_transit,

    -- Status
    current_status,
    is_complete

from {{ ref('int_order_milestones') }}
```

**Characteristics:**
- Multiple date columns (one per milestone)
- Rows are updated as process progresses
- Lag metrics between milestones
- Requires incremental logic with updates

---

### 4. Factless Fact Tables

**Grain:** Records events with no measurements

**Use Cases:**
- Student attendance (just presence/absence)
- Product eligibility (which products available in which regions)
- Promotion coverage (which customers eligible for which promotions)

**Example:**
```sql
-- fct_student_attendance.sql
-- Grain: One row per student per class session

select
    student_id,
    class_id,
    session_date,
    was_present,
    was_tardy
from {{ ref('stg_attendance') }}
```

**Characteristics:**
- No numerical facts (or just flags)
- Still valuable for coverage analysis
- Enables queries like "who was eligible but didn't participate?"

---

## Fact Table Best Practices

### 1. Define Clear Grain

Always document the grain at the top of the model:

```sql
{{
    config(
        materialized='table'
    )
}}

-- Grain: One row per order line item
-- Primary key: order_line_id (composite of order_id + line_item_number)
-- Foreign keys: order_id, product_id, customer_id
```

**Questions to answer:**
- What does one row represent?
- What is the primary key?
- What level of detail is captured?
- Can rows be updated or are they immutable?

### 2. Use Surrogate Keys When Needed

**When to use surrogate keys:**
- Natural key is multi-column composite
- Natural key is large (e.g., UUID)
- SCD Type 2 dimensions (need to join to specific version)

```sql
-- Generate surrogate key
{{ dbt_utils.generate_surrogate_key(['order_id', 'line_item_number']) }} as order_line_sk
```

### 3. Denormalize Strategically (SOMA Pattern)

**Denormalize when:**
- Attribute is frequently used in GROUP BY or WHERE
- Attribute is stable (doesn't change often)
- Simplifies 80% of queries

**Example:**
```sql
-- Instead of just foreign keys:
select
    order_id,
    customer_id,  -- FK only
    product_id    -- FK only
from orders

-- Denormalize frequently-used attributes:
select
    order_id,
    customer_id,
    customer_segment,   -- Denormalized
    customer_region,    -- Denormalized
    product_id,
    product_category,   -- Denormalized
    product_tier        -- Denormalized
from orders o
left join customers c on o.customer_id = c.customer_id
left join products p on o.product_id = p.product_id
```

### 4. Choose Appropriate Clustering

For large fact tables (> 1TB), add clustering keys:

```sql
{{
    config(
        materialized='table',
        cluster_by=['order_date', 'customer_segment']
    )
}}
```

**Clustering key selection:**
- Date columns (most selective)
- High-cardinality dimensions frequently filtered
- Order matters: most selective first

### 5. Use Incremental Models for Large Facts

Transaction fact tables often grow large quickly. Use incremental models:

```sql
{{
    config(
        materialized='incremental',
        unique_key='order_id',
        cluster_by=['order_date']
    )
}}

select * from {{ ref('stg_orders') }}

{% if is_incremental() %}
    where order_date > (select max(order_date) from {{ this }})
{% endif %}
```

---

## Common Fact Table Patterns

### Additive vs Semi-Additive vs Non-Additive Facts

| Type | Description | Example | Aggregation |
|------|-------------|---------|-------------|
| **Additive** | Can sum across all dimensions | `order_amount`, `quantity` | `SUM()` works for all dims |
| **Semi-Additive** | Can sum across some dimensions, not others | `account_balance` | Don't sum across time |
| **Non-Additive** | Cannot sum at all | `unit_price`, `percentage` | Use `AVG()` or weighted avg |

**Example:**
```sql
-- Additive fact: total revenue across all dimensions
select sum(order_amount) from fct_orders;

-- Semi-additive fact: account balance (don't sum across time)
select
    account_id,
    sum(ending_balance)  -- ❌ Wrong
from fct_account_balance_daily
group by account_id;

-- Correct for semi-additive:
select
    account_id,
    ending_balance  -- One row per account
from fct_account_balance_daily
qualify row_number() over (partition by account_id order by date_day desc) = 1;
```

### Derived Facts

Calculate facts from other facts when it simplifies queries:

```sql
select
    order_id,
    -- Source facts
    quantity,
    unit_price,
    discount_amount,
    tax_amount,
    shipping_cost,

    -- Derived facts (pre-calculated for convenience)
    quantity * unit_price as subtotal,
    (quantity * unit_price) - discount_amount as net_amount,
    (quantity * unit_price) - discount_amount + tax_amount + shipping_cost as total_amount

from {{ ref('stg_orders') }}
```

### Degenerate Dimensions

Store dimension attributes directly in fact table when they don't justify a separate dimension:

```sql
select
    order_id,
    customer_id,  -- FK to dim_customers

    -- Degenerate dimensions (no dim table)
    order_number,       -- Textual identifier
    invoice_number,     -- Low cardinality
    tracking_number,    -- Unique to this order
    internal_order_id   -- System identifier

from {{ ref('stg_orders') }}
```

**When to use degenerate dimensions:**
- Very low cardinality (2-5 values)
- Unique to one fact record (like order_number)
- No other attributes to group with it

---

## Testing Fact Tables

```yaml
models:
  - name: fct_orders
    columns:
      - name: order_id
        tests:
          - unique
          - not_null
      - name: customer_id
        tests:
          - not_null
          - relationships:
              to: ref('dim_customers')
              field: customer_id
      - name: order_amount
        tests:
          - not_null
          - dbt_utils.expression_is_true:
              expression: ">= 0"
      - name: order_date
        tests:
          - not_null
```

---

## Fact Table Anti-Patterns

### ❌ Mixed Grain

**Problem:** Different rows at different levels of detail

```sql
-- Bad: Mix of order-level and line-level rows
select * from fct_orders
-- Some rows are orders, some are line items
```

**Solution:** Separate into `fct_orders` and `fct_order_lines`

### ❌ Missing Foreign Keys

**Problem:** Can't join to dimensions

```sql
-- Bad: No way to join to customer dimension
select order_id, customer_name from fct_orders
```

**Solution:** Store `customer_id` FK, denormalize `customer_name` if frequently needed

### ❌ Over-Denormalization

**Problem:** Entire dimension copied into fact table

```sql
-- Bad: 50 customer columns in fact table
select
    order_id,
    customer_id,
    customer_name,
    customer_email,
    customer_phone,
    customer_address,
    customer_city,
    customer_state,
    -- ... 40 more customer columns
from fct_orders
```

**Solution:** Denormalize only frequently-used attributes (5-10 max)

### ❌ Calculated Facts Not Pre-Computed

**Problem:** Users repeat complex calculations

```sql
-- Bad: Users must calculate total amount every time
select
    order_id,
    quantity,
    unit_price,
    discount,
    tax,
    shipping
    -- No total_amount column
from fct_orders
```

**Solution:** Pre-calculate common derived facts

---

## Performance Optimization

### Clustering Strategy

```sql
{{
    config(
        cluster_by=['order_date', 'customer_segment']
    )
}}
```

**Impact:** 3-5x faster queries that filter on clustered columns

### Incremental Strategy

```sql
{{
    config(
        materialized='incremental',
        unique_key='order_id',
        incremental_strategy='merge'  -- or 'append', 'delete+insert'
    )
}}
```

**Impact:** 5-10x faster builds for large fact tables

### Partitioning (Clustering)

For very large tables (> 1TB), use micro-partitions via clustering:

```sql
{{
    config(
        cluster_by=['date_month', 'region']
    )
}}
```

**Impact:** 75% reduction in bytes scanned for date-filtered queries
