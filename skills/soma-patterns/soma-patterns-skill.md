---
name: soma-patterns
description: SOMA methodology patterns for data modeling and metrics. Use when: "SOMA layer", "activity vs entity", "net model", "atomic vs compound", "metric categorization", "SOMA rules", "layer placement", "naming conventions", "what layer does this go in", "is this an activity or entity", "SOMA compliance"
---

# SOMA Patterns Guide

Apply these SOMA (Standard Operating Metrics & Analytics) principles when working with SQL models, metrics, or data architecture in this project.

## Core Principle

> "Metrics must come first – and all other primitives, pipelines, and artifacts derive from those metrics."

Work **backwards** from metrics to models, then **forwards** to consumption.

---

## The Four Scopes of SOMA

### 1. Definitions Scope

Establish logical definitions, semantics, and metadata for:

**Metrics** - The core primitive with standardized definitions:
- **Atomic metrics**: Foundational, standalone measurements (count, sum, average)
- **Compound metrics**: Derived through mathematical expressions containing component metrics

**Terms** - Key business concepts and definitions

**Metric Categorization:**
| Category | Examples |
|----------|----------|
| Metric Sets (functional areas) | Pipeline, Product, Demand Gen, Loyalty, Financials |
| Owner Teams | Sales, Marketing, Product, Customer Success, Finance |
| Business Models | Subscription, NPS, CSAT, Usage-based |

### 2. Models Scope

Define foundational data structures through two abstraction layers:

**Activities (Event Streams)**:
- Business events captured as immutable data
- Append-only, immutable ledgers (event tables)
- Model businesses as "an immutable ledger of facts that happen in the business"
- More intuitive interface for reasoning about and understanding a business
- Improves auditability and pipeline manageability
- Can originate from source systems or synthesized through data pipelines

**Entities (Dimensional Tables)**:
- Wide fact and dimension tables
- Greater denormalization than classical dimensional modeling
- Support metric calculations across key dimensions

### 3. Expression Scope

Expose metrics to consumers through:

**Semantic Layers**:
- View definitions for LookML, Cube, dbt Metricflow, etc.
- Virtual abstraction layer integrated into BI platforms

**Nets (Pre-computed Metrics)**:
- Flattened OLAP cubes with metrics cached across dimensions
- Bi-temporal design supporting metric corrections over time
- Optimized for performance

### 4. Consumption Scope

How metrics are consumed, shared, and analyzed:
- Dashboard templates
- Standard analyses
- Exposures and visualizations

---

## SOMA Layer Flow

Data flows through these layers in order:

```
staging → activities → entities → metrics → nets → dashboards
```

**Rules:**
- Lower layers cannot reference higher layers
- Never skip layers
- `staging/` models are pre-SOMA (raw source data)

---

## Model Naming Conventions

| Layer | Prefix | Example |
|-------|--------|---------|
| Staging | `stg_` | `stg_salesforce__accounts` |
| Activities | `act_` | `act_subscription_started` |
| Facts | `fct_` | `fct_subscriptions` |
| Dimensions | `dim_` | `dim_customers` |
| Nets | `net_` | `net_mrr_metrics` |
| Dashboards | `dash_` | `dash_executive_kpis` |

**Full staging format:** `stg_<source>__<entity>` (double underscore)

---

## SOMA Implementation Workflow

When applying SOMA to architectural decisions:

### 1. Start with Metrics Selection (Definitions Scope)
- Identify the anchor metric set for the business domain
- Define atomic metrics first, then compound metrics
- Document formulas, business definitions, and caveats
- Categorize by functional area and owner team

### 2. Work Backwards (Models Scope)
- Identify required Activities (business events)
- Design Activity Streams as event tables
- Specify Entity structures (facts and dimensions)
- Map source data to Activities and Entities

### 3. Work Forwards (Expression & Consumption)
- Choose metric exposure method (Semantic Layer vs. Nets)
- Define how metrics are calculated from Activities/Entities
- Design dashboard templates and standard analyses
- Document metric relationships and dependencies

### 4. Apply Activity Schema Pattern
- Prefer event-based modeling over snapshot-based where appropriate
- Design immutable activity streams
- Use activities to drive metric calculations
- Maintain auditability through event history

---

## SOMA in dbt Projects

Structure dbt models to align with SOMA scopes:

```
models/
├── staging/              # Source system data (pre-SOMA)
│   └── stg_<source>__<entity>
├── activities/           # SOMA Models Scope - Activities
│   └── act_<event_name>  # e.g., act_subscription_started
├── entities/             # SOMA Models Scope - Entities
│   ├── fct_<entity>      # Fact tables
│   └── dim_<entity>      # Dimension tables
├── metrics/              # SOMA Definitions Scope
│   └── metrics.yml       # Metric definitions
└── marts/                # SOMA Expression/Consumption
    ├── nets/             # Pre-computed metric tables
    └── <domain>/         # Business domain marts
```

---

## Metric Types

### Atomic Metrics
Direct measurements that cannot be decomposed:
- Count, sum, average of raw data
- Examples: `new_customers`, `total_revenue`, `active_users`

### Compound Metrics
Derived from atomic metrics:
- Ratios, rates, percentages
- Examples: `customer_acquisition_cost`, `net_revenue_retention`, `ltv_cac_ratio`

**Always define atomic metrics first, then build compound metrics from them.**

---

## Activity Stream Pattern

Activities are immutable event logs:

```sql
select
    {{ dbt_utils.generate_surrogate_key(['source_id', 'occurred_at']) }} as activity_id,
    'event_name' as activity_type,
    occurred_at,           -- When event happened
    actor_id,              -- Who performed it
    object_id,             -- What was acted upon

    -- Event-specific attributes
    attribute_1,
    attribute_2,

    -- Context dimensions for slicing
    dimension_1,
    dimension_2,

    -- Metadata
    current_timestamp() as recorded_at,
    'source_system' as source_system

from {{ ref('stg_source') }}
```

**Activity Rules:**
- Always immutable (use `append` incremental strategy)
- Include `occurred_at` timestamp
- Include dimensions needed for metric slicing
- Unique `activity_id` per event

---

## Entity Pattern (Facts & Dimensions)

Denormalize dimensions into facts for performance:

```sql
select
    -- Primary key
    entity_id,

    -- Foreign keys
    dimension_1_id,
    dimension_2_id,

    -- Facts (measurements)
    amount,
    quantity,

    -- Denormalized dimensions (SOMA pattern)
    customer_segment,
    product_tier,
    region,

    -- Dates
    created_at,
    updated_at,

    -- Metadata
    current_timestamp() as _dbt_loaded_at

from {{ ref('int_enriched') }}
```

---

## Nets Pattern (Pre-computed Metrics)

Nets are flattened OLAP cubes with bi-temporal support:

```sql
select
    -- Grain
    date_month,
    customer_segment,
    product_tier,

    -- Atomic metrics
    count(distinct customer_id) as customer_count,
    sum(mrr_amount) as mrr,

    -- Compound metrics
    sum(mrr_amount) / nullif(count(distinct customer_id), 0) as arpu,

    -- Bi-temporal tracking
    current_timestamp() as measured_at,
    date_month as valid_from,
    coalesce(
        lead(date_month) over (partition by customer_segment, product_tier order by date_month),
        '9999-12-31'::date
    ) as valid_to

from {{ ref('fct_subscriptions') }}
group by 1, 2, 3
```

**Nets Rules:**
- Always include bi-temporal columns (`measured_at`, `valid_from`, `valid_to`)
- Pre-aggregate across key dimensions
- Materialize as table for performance
- Include both atomic and compound metrics

---

## Safe Division Pattern

Always protect against divide-by-zero:

```sql
-- Good
sum(revenue) / nullif(count(distinct customer_id), 0) as revenue_per_customer

-- Bad
sum(revenue) / count(distinct customer_id)  -- Can fail!
```

---

## Metric Definition Template

When defining metrics in YAML:

```yaml
metrics:
  - name: metric_name
    label: Human Readable Name
    type: sum|count|average|ratio
    sql: column_or_expression

    # Classification
    owner: finance|sales|product|marketing
    category: revenue|growth|efficiency|engagement
    metric_type: atomic|compound

    # Documentation
    description: What this metric measures
    business_definition: Plain English for stakeholders
    calculation_notes: Implementation details
    caveats: Known limitations

    # For compound metrics
    components:
      - atomic_metric_1
      - atomic_metric_2
```

---

## SOMA Red Flags

Watch for these anti-patterns:
- ❌ Defining metrics after building data models
- ❌ Inconsistent metric definitions across dashboards
- ❌ No clear distinction between atomic and compound metrics
- ❌ Missing metric ownership or categorization
- ❌ Bypassing activity streams for complex event logic
- ❌ Duplicate metric calculations in different models
- ❌ No bi-temporal support for metric corrections
- ❌ Skipping layers (staging directly to nets)
- ❌ Activities without occurred_at timestamp

---

## SOMA Success Indicators

You're applying SOMA well when:
- ✅ Metrics are defined before building transformations
- ✅ All metrics trace back to documented definitions
- ✅ Activity streams provide clear business event history
- ✅ Metrics are categorized by owner and functional area
- ✅ Compound metrics reference their atomic components
- ✅ One source of truth for each metric calculation
- ✅ Metrics can be corrected historically (bi-temporal)

---

## Quick Reference

**Starting a new metric?**
1. Check if it exists in Levers Labs Metrics Library
2. Define as atomic or compound
3. Identify required activities/entities
4. Work backwards to build models
5. Add to semantic layer or nets

**Building a new model?**
1. Determine SOMA layer (activity, entity, net)
2. Use correct naming prefix
3. Follow CTE pattern (imports → logic → final)
4. Include appropriate tests
5. Document grain and purpose

**Common Mistakes to Avoid:**
- Skipping layers (staging directly to nets)
- Missing bi-temporal columns in nets
- Compound metrics without atomic components defined
- Division without nullif protection
- Activities without occurred_at timestamp

---

## Project-Specific Examples

**This project's SOMA implementation:**

- **Metric definitions:** `definitions/metrics/*.json` (339 metrics)
- **Activities layer:** `models/activities/act_*.sql`
- **Entities layer:** `models/entities/dim_*.sql`, `models/atomic/*.sql`
- **Nets layer:** `models/expression/nets/nets_*.sql`

**Example metric from this project:**
```json
// definitions/metrics/GrossMarginPercent.json
{
  "Metric Label": "Gross Margin (%)",
  "Metric Ref": "GrossMarginPercent",
  "Components": "Gross Profit; Total Revenue",
  "Complexity": "Composite",
  "Metric Expression": "({GrossProfit} / {TotalRevenue}) * 100"
}
```

**Example activity from this project:**
- See `models/activities/` for activity stream patterns

**Example net from this project:**
- See `models/expression/nets/nets_revenue_metrics.sql` for bi-temporal pattern

---

## Memory Integration

When making SOMA decisions:

1. **Check past decisions:** `.claude/memory/reflections/architecture/`
2. **Query:** "How did we handle similar layer placement before?"
3. **Reference patterns:** `.claude/memory/patterns/`

After architectural decisions:

1. **Document rationale:** Store in `.claude/memory/reflections/architecture/`
2. **Update patterns:** If new pattern discovered
3. **Track what worked:** For future reference

---

## Key References

- **SOMA Framework**: https://github.com/Levers-Labs/SOMA-B2B-SaaS
- **Levers Labs Metrics Library**: https://www.leverslabs.com/metrics-library (400+ standard B2B SaaS metrics)
- **Project Metrics:** `definitions/metrics/` (339 JSON definitions)
- **Project Models:** `models/` organized by SOMA layer