---
name: metric-definition
description: Step-by-step workflow for defining new SOMA-compliant metrics. Use when: "add a metric", "define a metric", "create a KPI", "new metric", "metric definition", "how do I calculate", "measure this", "track this KPI", "metric template", "atomic vs compound metric"
---

# Metric Definition Workflow

Follow this workflow when defining new metrics in the analytics project.

## Step 1: Check Existing Metrics

Before creating a new metric:

1. **Check Levers Labs Metrics Library**: https://www.leverslabs.com/metrics-library
2. **Search existing definitions**: `grep -r "metric_name" definitions/metrics/`
3. **Check semantic layer**: Review `semantic/` directory

If a standard definition exists, use it. Only customize when truly unique.

## Step 2: Classify the Metric

### Determine Metric Type

**Atomic Metric** (foundational):
- Direct measurement from data
- Cannot be decomposed further
- Examples: `new_customers`, `total_revenue`, `active_subscriptions`

**Compound Metric** (derived):
- Mathematical combination of atomic metrics
- Has formula referencing other metrics
- Examples: `customer_acquisition_cost`, `net_revenue_retention`, `arpu`

### Determine Category

| Category | Description | Examples |
|----------|-------------|----------|
| Revenue | Money coming in | MRR, ARR, Total Revenue |
| Growth | Business expansion | New Customers, Expansion MRR |
| Efficiency | Cost effectiveness | CAC, LTV/CAC Ratio |
| Engagement | Product usage | DAU, MAU, Feature Adoption |
| Retention | Customer loyalty | Churn Rate, NRR |
| Pipeline | Sales funnel | Win Rate, Pipeline Value |

### Determine Owner

Who is accountable for this metric?
- **Finance**: Revenue, costs, efficiency metrics
- **Sales**: Pipeline, bookings, win rate
- **Marketing**: Leads, CAC, attribution
- **Product**: Usage, engagement, adoption
- **Customer Success**: Retention, NPS, health scores

## Step 3: Define the Metric

### Atomic Metric Template

```yaml
# definitions/metrics/<category>/<metric_name>.yml
metrics:
  - name: new_customers
    label: New Customers
    type: count_distinct
    sql: customer_id

    # Classification
    metric_type: atomic
    category: growth
    owner: sales
    business_model: subscription

    # Definition
    description: |
      Count of unique customers who made their first purchase in the period.
      A customer is counted once, in the period of their first transaction.

    business_definition: >
      The number of new customers acquired during a time period.

    # Calculation details
    calculation_notes: |
      - Counted by first purchase date, not signup date
      - Includes only customers with completed transactions
      - Excludes test accounts and internal users

    # Caveats
    caveats: |
      - Does not include trial users who haven't converted
      - A customer can only be "new" once in their lifetime

    # Filters
    filters:
      - field: is_first_purchase
        operator: '='
        value: 'true'
      - field: is_test_account
        operator: '='
        value: 'false'

    # Dimensions for slicing
    dimensions:
      - customer_segment
      - acquisition_channel
      - region
      - product_tier

    # Relationships
    related_metrics:
      - total_customers
      - customer_churn_rate
      - customer_acquisition_cost
```

### Compound Metric Template

```yaml
metrics:
  - name: customer_acquisition_cost
    label: Customer Acquisition Cost (CAC)
    type: ratio

    # Classification
    metric_type: compound
    category: efficiency
    owner: finance
    business_model: subscription

    # Definition
    description: |
      Total sales and marketing spend divided by the number of new customers acquired.
      Measures the average cost to acquire one new customer.

    business_definition: >
      How much we spend on average to acquire each new customer.

    # Formula (referencing atomic metrics)
    sql: ${sales_marketing_spend} / NULLIF(${new_customers}, 0)

    # Component metrics
    components:
      - name: sales_marketing_spend
        description: Total S&M expenses in the period
      - name: new_customers
        description: Count of new customers acquired

    # Calculation details
    calculation_notes: |
      CAC = (Sales Costs + Marketing Costs) / New Customers

      Sales Costs include:
      - Sales team salaries and commissions
      - Sales tools and software
      - Travel and entertainment

      Marketing Costs include:
      - Advertising spend
      - Marketing team salaries
      - Events and sponsorships
      - Content production

    # Caveats
    caveats: |
      - Blended CAC (not segmented by channel)
      - Assumes same-period attribution
      - Does not account for brand spend vs performance spend

    # Time considerations
    time_grains:
      - monthly
      - quarterly
      - annual

    # Benchmarks (optional)
    benchmarks:
      good: '< $500'
      average: '$500 - $1000'
      poor: '> $1000'
```

## Step 4: Validate the Definition

### Definition Quality Checklist

- [ ] **Name**: Clear, unambiguous, snake_case
- [ ] **Label**: Human-readable display name
- [ ] **Type**: Correct aggregation (sum, count, average, ratio)
- [ ] **Category**: Assigned to appropriate functional area
- [ ] **Owner**: Team accountability identified
- [ ] **Description**: Technical definition with details
- [ ] **Business Definition**: Plain English for stakeholders
- [ ] **Calculation Notes**: How it's computed
- [ ] **Caveats**: Known limitations documented
- [ ] **Filters**: Any implicit filters specified
- [ ] **Dimensions**: Slicing dimensions identified

### Atomic Metrics
- [ ] Cannot be decomposed into simpler metrics
- [ ] Direct measurement from source data
- [ ] SQL references actual columns

### Compound Metrics
- [ ] Components listed and defined
- [ ] Formula uses `${metric_name}` syntax
- [ ] Safe division with NULLIF
- [ ] Component metrics exist as atomic

## Step 5: Document Dependencies

### Identify Required Data

1. **What activities are needed?**
   - Events that contribute to this metric
   - Example: `act_customer_created` for `new_customers`

2. **What entities are needed?**
   - Facts and dimensions required
   - Example: `fct_customers`, `dim_acquisition_channels`

3. **What existing metrics are components?**
   - For compound metrics only
   - List all atomic metrics in the formula

### Dependency Map

```
[Metric: customer_acquisition_cost]
    │
    ├── [Atomic: sales_marketing_spend]
    │       └── fct_expenses
    │           └── stg_netsuite__expenses
    │
    └── [Atomic: new_customers]
            └── fct_customers
                └── act_customer_created
                    └── stg_salesforce__accounts
```

## Step 6: Implement the Metric

### Option A: Semantic Layer (Preferred for ad-hoc)

Add to `semantic/metrics.yml`:

```yaml
metrics:
  - name: new_customers
    type: simple
    label: New Customers
    type_params:
      measure: customer_count
    filter: |
      {{ Dimension('is_first_purchase') }} = true
```

### Option B: Nets (Preferred for dashboards)

Create pre-computed metric in `models/marts/nets/`:

```sql
-- net_customer_acquisition.sql
SELECT
    date_month,
    acquisition_channel,
    customer_segment,

    -- Atomic metrics
    count(distinct customer_id) as new_customers,
    sum(sales_marketing_spend) as sales_marketing_spend,

    -- Compound metrics
    sum(sales_marketing_spend) / nullif(count(distinct customer_id), 0) as cac,

    -- Bi-temporal
    current_timestamp() as measured_at,
    date_month as valid_from,
    '9999-12-31'::date as valid_to

FROM {{ ref('fct_customer_acquisition') }}
GROUP BY 1, 2, 3
```

## Step 7: Add Tests

### Metric Validation Tests

```yaml
# schema.yml
models:
  - name: net_customer_acquisition
    tests:
      # Metric should be positive
      - dbt_utils.expression_is_true:
          expression: "new_customers >= 0"

      # CAC should be reasonable
      - dbt_utils.expression_is_true:
          expression: "cac >= 0"
          config:
            severity: warn

      # No nulls in required dimensions
      - dbt_utils.expression_is_true:
          expression: "date_month is not null"
```

### Cross-Validation

```sql
-- tests/assert_cac_formula.sql
-- Verify compound metric matches component calculation
SELECT *
FROM {{ ref('net_customer_acquisition') }}
WHERE abs(cac - (sales_marketing_spend / nullif(new_customers, 0))) > 0.01
```

## Quick Reference

### Metric Types by Aggregation

| Type | SQL Pattern | Example |
|------|-------------|---------|
| count | `COUNT(*)` | Total Orders |
| count_distinct | `COUNT(DISTINCT col)` | Unique Customers |
| sum | `SUM(col)` | Total Revenue |
| average | `AVG(col)` | Avg Order Value |
| ratio | `SUM(a) / NULLIF(SUM(b), 0)` | Conversion Rate |
| min/max | `MIN(col)`, `MAX(col)` | First Purchase Date |

### Common Metric Patterns

**Growth Rate**:
```sql
(current_value - previous_value) / nullif(previous_value, 0) * 100
```

**Retention Rate**:
```sql
retained_customers / nullif(starting_customers, 0) * 100
```

**Per-Unit Metric**:
```sql
total_value / nullif(unit_count, 0)
```

**Ratio**:
```sql
numerator / nullif(denominator, 0)
```

---

## Workflow Gates (Sequential Orchestration)

**IMPORTANT**: Each gate must pass before proceeding to the next step. If a gate fails, resolve the issue before continuing.

| Step | Gate | Pass Criteria | If Fails |
|------|------|---------------|----------|
| **Step 1** | ✋ **Uniqueness Gate** | Metric doesn't exist | Use existing definition |
| **Step 2** | ✋ **Classification Gate** | Type and category assigned | Review classification criteria |
| **Step 3** | ✋ **Definition Gate** | All required fields completed | Fill missing template fields |
| **Step 4** | ✋ **Validation Gate** | All checklist items pass | Fix validation errors |
| **Step 5** | ✋ **Dependency Gate** | All dependencies identified | Map missing dependencies |
| **Step 6** | ✋ **Implementation Gate** | Metric builds successfully | Debug implementation errors |
| **Step 7** | ✋ **Testing Gate** | All tests pass | Fix failing tests |

**Iterative Refinement**: If any gate fails, loop back to fix the issue. Common pattern:
```
Step 4: Validation ❌ → Back to Step 3: Fix definition → Step 4: Validation ✅ → Proceed to Step 5
```

---

## Troubleshooting

### Issue: "Should this be atomic or compound?"

**Symptom:** Unclear if metric is foundational or derived

**Decision Tree:**
1. Can you measure it directly from source data? → **Atomic**
2. Does it require combining other metrics? → **Compound**
3. Is there a mathematical formula with metric references? → **Compound**

**Examples:**
- `new_customers` = Direct count from data → **Atomic**
- `cac` = spend / customers → **Compound** (needs 2 atomic metrics)

### Issue: "Metric already exists but with different logic"

**Symptom:** Found existing metric but calculation differs

**Resolution:**
1. **If existing logic is correct:** Use existing, don't create duplicate
2. **If existing logic is wrong:** Fix existing metric (don't create new one)
3. **If both are valid:** Different metrics, add distinguishing suffix (e.g., `cac_blended` vs `cac_by_channel`)

### Issue: "Component metric doesn't exist yet"

**Symptom:** Compound metric needs atomic metric that isn't defined

**Resolution:**
1. Define the atomic metric first (follow this workflow for it)
2. Then define the compound metric that uses it
3. Order matters: atomics before compounds

### Issue: "Tests failing in Step 7"

**Common Causes:**

| Test Failure | Cause | Fix |
|--------------|-------|-----|
| Metric is null | Missing data or wrong filters | Check source data exists, adjust filters |
| Metric is negative | Wrong formula or bad data | Add NULLIF, validate source data |
| Metric unreasonably high | No filters applied | Add test/internal user filters |
| Metric doesn't match expected | Formula error | Validate formula against business definition |

### Issue: "Dimension collision in nets"

**Symptom:** Same dimension value has different meanings across time

**Resolution:** See `functional-testing` skill for dimension collision patterns

---

## Memory Integration

### Before Defining a New Metric

**Check existing definitions first:**

1. **Search project metrics**: `definitions/metrics/`
   ```bash
   grep -r "metric_name" definitions/metrics/
   ```

2. **Check Levers Labs Library**: https://www.leverslabs.com/metrics-library
   - 400+ standard B2B SaaS metrics with definitions

3. **Review past metric work**: `.claude/memory/reflections/metrics/`
   - "Have we defined a similar metric before?"
   - "What issues did we encounter with similar metrics?"

### Metric Definition Checklist

Before finalizing any metric:

```markdown
## Pre-Definition Checklist

- [ ] Searched existing definitions (no duplicate)
- [ ] Checked Levers Labs for standard definition
- [ ] Classified as atomic or compound
- [ ] Identified component metrics (if compound)
- [ ] Documented formula with NULLIF protection
- [ ] Listed all required dimensions
- [ ] Identified caveats and edge cases
- [ ] Named owner/team
```

### After Defining a Metric

Store the definition and any learnings:

1. **Document in metrics file**: `definitions/metrics/<category>/<metric>.yml`

2. **Store reflection**: `.claude/memory/reflections/metrics/`
   ```markdown
   ## Metric Definition - [metric_name]

   **Date:** YYYY-MM-DD
   **Type:** Atomic/Compound
   **Category:** [Revenue/Growth/Efficiency/...]

   **Key Decisions:**
   - [Why this formula]
   - [Why these filters]

   **Caveats Discovered:**
   - [Edge cases found]

   **Related Metrics:**
   - [Dependencies]
   ```

### Project Metric Patterns

**Standard atomic metrics in this project:**
- `new_customers` - Count of first-time purchasers
- `total_revenue` - Sum of completed order amounts
- `active_subscriptions` - Count of active subscription records

**Standard compound metrics:**
- `cac` = sales_marketing_spend / new_customers
- `arpu` = total_revenue / active_customers
- `nrr` = (starting_mrr + expansion - contraction - churn) / starting_mrr
