# Slowly Changing Dimensions (SCD)

Comprehensive guide to handling dimension changes over time in Snowflake.

## SCD Fundamentals

**What are Slowly Changing Dimensions?**
- Dimension attributes that change over time
- Requires strategy for handling historical changes
- Trade-off between history tracking and simplicity

**Types:**
- **Type 1**: Overwrite (no history)
- **Type 2**: Track history with versioning
- **Type 3**: Keep current + previous value only
- **Type 4**: Separate history table
- **Type 6**: Hybrid (2 + 3)

---

## SCD Type 1: Overwrite

**Use when:** History doesn't matter, just keep current value

### Implementation

```sql
-- Simple overwrite - no special handling needed
{{
    config(
        materialized='table'
    )
}}

select
    customer_id,
    customer_name,         -- Just update when it changes
    customer_segment,
    customer_email,
    current_timestamp() as _dbt_loaded_at
from {{ ref('stg_customers') }}
```

### Characteristics

- **Pros:**
  - Simple to implement
  - No extra storage
  - Easy to query
  - Fast performance

- **Cons:**
  - Loses history
  - Can't analyze historical trends
  - Can't restate past reports

### When to Use Type 1

- Correcting data errors
- Attributes that don't need history (e.g., phone number formatting)
- Non-critical attributes
- Storage/performance constraints

### Example Use Cases

```sql
-- Customer contact info (correct errors)
update dim_customers
set customer_email = 'corrected@email.com'
where customer_id = 123;

-- Product attributes (minor corrections)
update dim_products
set product_description = 'Updated description'
where product_id = 'ABC123';
```

---

## SCD Type 2: Track History

**Use when:** Need to track historical changes with validity periods

### Implementation (Manual Approach)

```sql
{{
    config(
        materialized='incremental',
        unique_key='customer_sk'
    )
}}

with

source as (
    select
        customer_id,
        customer_name,
        customer_segment,
        updated_at
    from {{ ref('stg_customers') }}
),

{% if is_incremental() %}
-- Get existing current records
existing_current as (
    select *
    from {{ this }}
    where is_current = true
),

-- Identify records that have changed
changes as (
    select
        s.customer_id,
        s.customer_name,
        s.customer_segment,
        s.updated_at
    from source s
    inner join existing_current e
        on s.customer_id = e.customer_id
    where s.customer_name != e.customer_name
       or s.customer_segment != e.customer_segment
),

-- Close out old records
closed_records as (
    select
        customer_sk,
        customer_id,
        customer_name,
        customer_segment,
        valid_from,
        current_date() as valid_to,  -- Close the record
        false as is_current           -- No longer current
    from existing_current
    where customer_id in (select customer_id from changes)
),
{% endif %}

-- New and changed records
new_records as (
    select
        {{ dbt_utils.generate_surrogate_key(['customer_id', 'updated_at']) }} as customer_sk,
        customer_id,
        customer_name,
        customer_segment,
        updated_at as valid_from,
        '9999-12-31'::date as valid_to,
        true as is_current
    from source

    {% if is_incremental() %}
    -- Only insert new or changed records
    where customer_id in (select customer_id from changes)
       or customer_id not in (select customer_id from existing_current)
    {% endif %}
)

{% if is_incremental() %}
select * from closed_records
union all
{% endif %}
select * from new_records
```

### Characteristics

- **Pros:**
  - Complete history preserved
  - Can analyze historical trends
  - Can restate past reports
  - Point-in-time accuracy

- **Cons:**
  - More complex queries (need to join on valid dates)
  - Larger storage requirements
  - More complex ETL logic

### Querying Type 2 Dimensions

```sql
-- Get current records only
select *
from dim_customers
where is_current = true;

-- Get historical record for specific date
select *
from dim_customers
where customer_id = 123
  and '2023-01-15' between valid_from and valid_to;

-- Join fact to dimension at fact's date
select
    f.order_id,
    f.order_date,
    c.customer_name,
    c.customer_segment  -- As of order_date
from fct_orders f
join dim_customers c
    on f.customer_id = c.customer_id
    and f.order_date between c.valid_from and c.valid_to;
```

---

## SCD Type 2 with dbt Snapshots (Recommended)

**Easiest approach:** Use dbt's built-in snapshot functionality

### Implementation

```sql
-- snapshots/customer_snapshot.sql
{% snapshot customer_snapshot %}

{{
    config(
        target_schema='snapshots',
        unique_key='customer_id',
        strategy='timestamp',
        updated_at='updated_at'
    )
}}

select * from {{ source('raw', 'customers') }}

{% endsnapshot %}
```

### Run Snapshots

```bash
# Run snapshot (creates or updates snapshot table)
dbt snapshot

# Run on schedule (daily)
dbt snapshot --select customer_snapshot
```

### Use Snapshot in Dimension

```sql
-- dim_customers.sql
{{
    config(
        materialized='view'  -- Snapshot already materialized
    )
}}

select
    customer_id,
    customer_name,
    customer_segment,
    dbt_valid_from as valid_from,
    dbt_valid_to as valid_to,
    dbt_valid_to is null as is_current,
    dbt_updated_at as _dbt_loaded_at
from {{ ref('customer_snapshot') }}
```

### Snapshot Strategies

**1. Timestamp Strategy** (Recommended)

```sql
{{
    config(
        strategy='timestamp',
        updated_at='updated_at'
    )
}}
```

- Compares `updated_at` column to detect changes
- Most reliable if source system maintains timestamps

**2. Check Strategy**

```sql
{{
    config(
        strategy='check',
        check_cols=['customer_name', 'customer_segment']
    )
}}
```

- Checks specific columns for changes
- Use when no `updated_at` column available

**3. Check All Columns**

```sql
{{
    config(
        strategy='check',
        check_cols='all'
    )
}}
```

- Checks all columns for changes
- Can be slow for wide tables

---

## SCD Type 3: Current + Previous

**Use when:** Only need current and one previous value

### Implementation

```sql
{{
    config(
        materialized='table'
    )
}}

with

source_with_lag as (
    select
        customer_id,
        customer_name,
        customer_segment,
        updated_at,
        lag(customer_segment) over (
            partition by customer_id
            order by updated_at
        ) as previous_segment,
        row_number() over (
            partition by customer_id
            order by updated_at desc
        ) as rn
    from {{ ref('stg_customers') }}
)

select
    customer_id,
    customer_name,
    customer_segment as current_segment,
    previous_segment,
    updated_at
from source_with_lag
where rn = 1  -- Current record only
```

### Characteristics

- **Pros:**
  - Simple to query (one row per entity)
  - Can track one change
  - No complex date joins

- **Cons:**
  - Limited history (only current + previous)
  - Can't analyze long-term trends
  - Loses intermediate changes

### When to Use Type 3

- Tracking simple before/after (e.g., status changes)
- Limited reporting needs
- Simplicity more important than complete history

### Example Use Cases

```sql
-- Track customer segment changes
select
    customer_id,
    current_segment,
    previous_segment,
    case
        when current_segment != previous_segment then 'Changed'
        else 'Stable'
    end as segment_status
from dim_customers;

-- Analyze segment transitions
select
    previous_segment,
    current_segment,
    count(*) as customer_count
from dim_customers
where previous_segment is not null
group by 1, 2
order by 3 desc;
```

---

## SCD Type 4: Separate History Table

**Use when:** Need history but want fast current dimension queries

### Implementation

```sql
-- dim_customers.sql (current only)
{{
    config(
        materialized='table'
    )
}}

select
    customer_id,
    customer_name,
    customer_segment,
    current_timestamp() as _dbt_loaded_at
from {{ ref('stg_customers') }}
```

```sql
-- dim_customers_history.sql (full history)
{{
    config(
        materialized='incremental',
        unique_key='history_sk'
    )
}}

select
    {{ dbt_utils.generate_surrogate_key(['customer_id', 'updated_at']) }} as history_sk,
    customer_id,
    customer_name,
    customer_segment,
    updated_at as valid_from,
    lead(updated_at, 1, '9999-12-31'::date) over (
        partition by customer_id
        order by updated_at
    ) as valid_to
from {{ ref('stg_customers') }}

{% if is_incremental() %}
where updated_at > (select max(valid_from) from {{ this }})
{% endif %}
```

### Characteristics

- **Pros:**
  - Fast current dimension queries
  - Full history in separate table
  - Clean separation of concerns

- **Cons:**
  - Two tables to maintain
  - More complex joins for historical queries

---

## SCD Type 6: Hybrid (2 + 3)

**Use when:** Need full history AND easy access to current/previous

### Implementation

```sql
{{
    config(
        materialized='incremental',
        unique_key='customer_sk'
    )
}}

select
    {{ dbt_utils.generate_surrogate_key(['customer_id', 'valid_from']) }} as customer_sk,
    customer_id,
    customer_name,
    customer_segment,

    -- Type 2: History tracking
    valid_from,
    valid_to,
    is_current,

    -- Type 3: Current values (denormalized)
    last_value(customer_segment) over (
        partition by customer_id
        order by valid_from
        rows between unbounded preceding and unbounded following
    ) as current_segment

from {{ ref('customer_snapshot') }}
```

---

## Best Practices

### 1. Choose the Right SCD Type

| Requirement | Recommended Type |
|-------------|------------------|
| No history needed | Type 1 |
| Full history needed | Type 2 (with dbt snapshots) |
| Simple before/after | Type 3 |
| Fast current queries + history | Type 4 |

### 2. Use dbt Snapshots for Type 2

**Advantages:**
- Built-in functionality
- Automatic history tracking
- Standardized approach
- Less custom code

**Setup:**
```bash
# Initialize snapshots
dbt snapshot

# Schedule daily
dbt snapshot --select customer_snapshot
```

### 3. Index Validity Dates

For Type 2 dimensions, ensure efficient date range queries:

```sql
{{
    config(
        cluster_by=['customer_id', 'valid_from']
    )
}}
```

### 4. Test SCD Logic

```yaml
# tests/assert_no_overlapping_validity_periods.sql
select
    customer_id,
    count(*) as overlapping_periods
from dim_customers
where is_current = true
group by 1
having count(*) > 1
```

### 5. Document SCD Strategy

Always document in model:

```sql
-- SCD Type: 2 (via dbt snapshot)
-- Grain: One row per customer per validity period
-- Primary key: customer_sk (surrogate)
-- Natural key: customer_id
-- Validity: valid_from, valid_to, is_current
```

---

## Common Patterns

### Handling Late-Arriving Changes

```sql
-- Backfill historical change
-- Update existing records to close them out
update dim_customers
set
    valid_to = '2023-01-15',
    is_current = false
where customer_id = 123
  and is_current = true;

-- Insert new historical record
insert into dim_customers (...)
values (..., '2023-01-15', '9999-12-31', true);
```

### Merging Multiple Snapshots

```sql
-- Combine snapshots from multiple sources
select * from {{ ref('customer_snapshot_system_a') }}
union all
select * from {{ ref('customer_snapshot_system_b') }}
```

---

## Performance Optimization

### Clustering for Type 2

```sql
{{
    config(
        cluster_by=['customer_id', 'valid_from']
    )
}}
```

**Impact:** 3-5x faster historical queries

### Incremental Snapshots

```sql
{{
    config(
        materialized='incremental',
        unique_key='customer_sk'
    )
}}
```

**Impact:** 10x faster snapshot processing

### Partitioning by Date

For very large Type 2 dimensions, partition by `valid_from`:

```sql
{{
    config(
        cluster_by=['valid_from', 'customer_segment']
    )
}}
```

---

## Troubleshooting

### Issue: Duplicate Current Records

**Symptom:** Multiple `is_current = true` rows for same entity

**Diagnosis:**
```sql
select
    customer_id,
    count(*) as current_count
from dim_customers
where is_current = true
group by 1
having count(*) > 1;
```

**Fix:** Ensure snapshot uniqueness logic is correct

### Issue: Missing History

**Symptom:** Expected historical record not found

**Diagnosis:**
```sql
-- Check snapshot ran
select max(dbt_updated_at) from dim_customers;

-- Check for change detection
select * from {{ ref('stg_customers') }}
where customer_id = 123
  and updated_at > (select max(dbt_updated_at) from dim_customers);
```

**Fix:** Run `dbt snapshot` or check `updated_at` column

### Issue: Slow Historical Queries

**Symptom:** Queries filtering by date range are slow

**Diagnosis:**
```sql
-- Check if clustering is enabled
show tables like 'dim_customers';
```

**Fix:** Add clustering on `valid_from` or `customer_id`
