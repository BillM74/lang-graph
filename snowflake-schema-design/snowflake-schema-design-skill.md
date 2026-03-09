---
name: snowflake-schema-design
description: Snowflake schema design patterns including dimensional modeling, fact/dimension tables, and slowly changing dimensions. Use when: "design schema", "create fact table", "create dimension", "dimensional modeling", "slowly changing dimension", "SCD type 2", "schema architecture", "data warehouse design", "star schema"
---

# Snowflake Schema Design Guide

Quick reference for designing effective Snowflake schemas following dimensional modeling principles.

## Core Concepts

| Term | Definition | Example |
|------|------------|---------|
| **Fact Table** | Contains measurements/metrics at specific grain | `fct_orders`, `fct_subscriptions` |
| **Dimension Table** | Contains descriptive attributes | `dim_customers`, `dim_products` |
| **Grain** | What one row represents | "One row per order" |
| **Surrogate Key** | System-generated unique identifier | `customer_sk` |
| **Natural Key** | Business identifier from source | `customer_id` |

---

## Star Schema Pattern

```
          dim_customers
               │
               │
dim_products──fct_orders──dim_dates
               │
               │
          dim_locations
```

**Benefits:**
- Simple to understand and query
- Optimized for analytical workloads
- Clear separation of facts and dimensions

---

## Fact vs Dimension Decision

| Characteristic | Fact Table | Dimension Table |
|----------------|------------|-----------------|
| **Purpose** | Measurements/events | Descriptive context |
| **Grain** | Transaction or snapshot | One row per entity |
| **Size** | Large (millions+ rows) | Smaller (thousands to millions) |
| **Columns** | Mostly numeric | Mostly text/categorical |
| **Keys** | Natural + foreign keys | Natural + surrogate keys |
| **Updates** | Append-mostly | Update-in-place or versioned |

---

## Fact Table Quick Reference

### Fact Table Types

| Type | Grain | Example | Details |
|------|-------|---------|---------|
| **Transaction** | One row per event | `fct_orders` | [See guide →](references/fact-table-design.md#1-transaction-fact-tables) |
| **Periodic Snapshot** | One row per period per entity | `fct_account_balance_daily` | [See guide →](references/fact-table-design.md#2-periodic-snapshot-fact-tables) |
| **Accumulating Snapshot** | One row per process | `fct_order_fulfillment` | [See guide →](references/fact-table-design.md#3-accumulating-snapshot-fact-tables) |
| **Factless Fact** | Events with no measurements | `fct_student_attendance` | [See guide →](references/fact-table-design.md#4-factless-fact-tables) |

### Must-Have Components

```sql
select
    -- Primary key (surrogate or natural)
    order_id,

    -- Foreign keys to dimensions
    customer_id,
    product_id,

    -- Date keys
    order_date,

    -- Facts (measurements)
    order_amount,
    quantity,

    -- Denormalized dimensions (SOMA pattern)
    customer_segment,
    product_category

from {{ ref('stg_orders') }}
```

**Detailed fact table patterns**: [references/fact-table-design.md](references/fact-table-design.md)

---

## Dimension Table Quick Reference

### Common Dimension Types

| Type | Purpose | Example |
|------|---------|---------|
| **Standard** | Business entity | `dim_customers` |
| **Date** | Time intelligence | `dim_date` |
| **Bridge** | Many-to-many resolver | `bridge_customer_accounts` |
| **Junk** | Low-cardinality flags | `dim_order_flags` |

### Must-Have Components

```sql
select
    -- Surrogate key
    {{ dbt_utils.generate_surrogate_key(['customer_id']) }} as customer_sk,

    -- Natural key
    customer_id,

    -- Attributes
    customer_name,
    customer_email,

    -- Hierarchies
    customer_segment,
    region,
    country,

    -- Derived attributes
    case
        when lifetime_value >= 10000 then 'platinum'
        else 'gold'
    end as value_tier,

    -- Flags
    is_active

from {{ ref('stg_customers') }}
```

**Detailed dimension patterns**: [references/dimension-table-design.md](references/dimension-table-design.md)

---

## Slowly Changing Dimensions (SCD)

### SCD Type Decision Matrix

| Type | History Tracking | Use When | Implementation |
|------|------------------|----------|----------------|
| **Type 1** | None (overwrite) | History doesn't matter | Simple table |
| **Type 2** | Full history | Need historical analysis | dbt snapshots |
| **Type 3** | Current + previous | Simple before/after | LAG window function |

### Type 1: Overwrite (No History)

```sql
-- Simple overwrite
select
    customer_id,
    customer_name,
    customer_segment  -- Just update when it changes
from {{ ref('stg_customers') }}
```

**When to use:** Correcting errors, non-critical attributes

### Type 2: Track History (Recommended)

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

**Query pattern:**
```sql
-- Get current records
select * from {{ ref('customer_snapshot') }}
where dbt_valid_to is null;

-- Join fact to historical dimension
select
    f.order_id,
    c.customer_name,
    c.customer_segment  -- As of order_date
from fct_orders f
join {{ ref('customer_snapshot') }} c
    on f.customer_id = c.customer_id
    and f.order_date between c.dbt_valid_from and coalesce(c.dbt_valid_to, '9999-12-31');
```

**Detailed SCD patterns**: [references/slowly-changing-dimensions.md](references/slowly-changing-dimensions.md)

---

## Design Guidelines

### 1. Define Clear Grain

Always document the grain at the top of the model:

```sql
-- Grain: One row per order line item
-- Primary key: order_line_id (composite of order_id + line_item_number)
```

**Questions to answer:**
- What does one row represent?
- What is the primary key?
- What level of detail is captured?

### 2. Denormalization Strategy (SOMA Pattern)

**Denormalize when:**
- Frequently used in GROUP BY or WHERE
- Stable attributes (don't change often)
- Simplifies downstream queries

```sql
-- Denormalize frequently-used attributes
select
    order_id,
    customer_id,
    customer_segment,   -- Denormalized
    product_id,
    product_category    -- Denormalized
from orders o
left join customers c on o.customer_id = c.customer_id
left join products p on o.product_id = p.product_id
```

### 3. Naming Conventions

| Type | Prefix | Example |
|------|--------|---------|
| Fact table | `fct_` | `fct_orders` |
| Dimension table | `dim_` | `dim_customers` |
| Bridge table | `bridge_` | `bridge_customer_accounts` |
| Staging | `stg_` | `stg_salesforce__accounts` |

---

## SOMA Schema Patterns

### Activity Table Pattern (`act_*`)

```sql
-- Grain: One event occurrence
-- Always includes: activity_id, entity_id, occurred_at

CREATE TABLE act_event_name (
    activity_id VARCHAR PRIMARY KEY,    -- Surrogate key
    entity_id VARCHAR NOT NULL,          -- FK to entity
    occurred_at TIMESTAMP NOT NULL,      -- When event happened
    activity_type VARCHAR NOT NULL,      -- Event classification
    _loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);
```

### Entity Table Pattern (`fct_*`, `dim_*`)

```sql
-- Grain: One instance of a business object
-- Always includes: entity_id, is_current (for SCD2)

CREATE TABLE fct_entity (
    entity_sk VARCHAR PRIMARY KEY,       -- Surrogate key
    entity_id VARCHAR NOT NULL,          -- Natural key
    dimension_id VARCHAR,                -- Dimension FKs
    -- SCD2 fields (if applicable)
    valid_from DATE,
    valid_to DATE,
    is_current BOOLEAN,
    _loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);
```

### Net Table Pattern (`net_*`)

```sql
-- Grain: One time period per dimension combination
-- Always includes: bi-temporal columns

CREATE TABLE net_metric_set (
    -- Grain columns (composite PK)
    date_month DATE NOT NULL,
    customer_segment VARCHAR NOT NULL,
    -- Metrics
    metric_1 NUMERIC,
    metric_2 NUMERIC,
    -- Bi-temporal columns (required)
    measured_at TIMESTAMP NOT NULL,
    valid_from DATE NOT NULL,
    valid_to DATE NOT NULL,
    _loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);
```

---

## Common Anti-Patterns to Avoid

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| **Massive wide tables** | 200+ columns in one table | Separate into fact + dimensions |
| **Mixed grain** | Orders + line items in same table | Separate `fct_orders` and `fct_order_lines` |
| **Over-normalization** | 15 joins for simple query | Strategic denormalization |
| **Missing surrogate keys** | Relying only on natural keys | Add surrogate keys for SCD2 |
| **No clear grain** | Unclear what one row represents | Document grain at top of model |

---

## Testing Schema Design

```yaml
# Fact table tests
models:
  - name: fct_orders
    columns:
      - name: order_id
        tests:
          - unique
          - not_null
      - name: customer_id
        tests:
          - relationships:
              to: ref('dim_customers')
              field: customer_id

# Dimension table tests
models:
  - name: dim_customers
    columns:
      - name: customer_sk
        tests:
          - unique
          - not_null
      - name: customer_segment
        tests:
          - accepted_values:
              values: ['enterprise', 'mid-market', 'smb']
```

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

**For fact tables:** Date + high-cardinality dimension
**For Type 2 dimensions:** Entity ID + valid_from

### Incremental Models

For large transaction fact tables:

```sql
{{
    config(
        materialized='incremental',
        unique_key='order_id'
    )
}}

select * from {{ ref('stg_orders') }}
{% if is_incremental() %}
    where order_date > (select max(order_date) from {{ this }})
{% endif %}
```

---

## Detailed Guides

For comprehensive schema design patterns:

- **[Fact Table Design](references/fact-table-design.md)** - Transaction, snapshot, accumulating, and factless fact patterns with full examples
- **[Dimension Table Design](references/dimension-table-design.md)** - Standard, date, bridge, junk, and conformed dimension patterns
- **[Slowly Changing Dimensions](references/slowly-changing-dimensions.md)** - Type 1, 2, 3, 4, and 6 patterns with dbt snapshot implementation

---

## Memory Integration

### Before Designing Schemas

Query the memory system:
- **Check past architecture decisions**: `.claude/memory/reflections/architecture/`
- **Review existing patterns**: Check existing models for consistent patterns

### After Schema Design

Store decisions in memory:

```markdown
// Add to .claude/memory/reflections/architecture/
## Schema Decision - [Entity Name]

**Date:** YYYY-MM-DD
**Decision:** [Grain, key structure, SCD type]
**Rationale:** [Why this approach]
**Trade-offs:** [What was sacrificed]
**Future Considerations:** [When to revisit]
```
