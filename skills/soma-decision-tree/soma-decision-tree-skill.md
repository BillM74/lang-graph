---
name: soma-decision-tree
description: Quick reference for determining correct SOMA layer placement. Use when: "what layer does this go in", "activity or entity", "where does this belong", "SOMA layer decision", "classify this model", "is this an activity", "staging or entity", "net vs entity"
---

# SOMA Decision Tree

Quick reference for determining the correct SOMA layer placement.

## The Core Question: Activity or Entity?

Use this decision tree when you're unsure where data belongs.

```
START: What kind of data is this?
│
├─► Is it an EVENT that happened at a specific point in time?
│   │
│   ├─► YES: Can it be modified/updated after it occurs?
│   │   │
│   │   ├─► NO (immutable): → ACTIVITY
│   │   │   Examples: order_placed, email_sent, page_viewed
│   │   │
│   │   └─► YES (mutable): → Consider as ENTITY state change
│   │       Create activity from the state change instead
│   │
│   └─► NO: Continue below ↓
│
├─► Is it a THING with attributes that can change over time?
│   │
│   ├─► YES: → ENTITY
│   │   Examples: customer, product, account, subscription
│   │
│   └─► NO: Continue below ↓
│
├─► Is it a PRE-COMPUTED METRIC or TIME-SERIES aggregation?
│   │
│   ├─► YES: → NET
│   │   Examples: daily_revenue, monthly_active_users
│   │
│   └─► NO: Continue below ↓
│
└─► Is it RAW data that needs cleaning/renaming?
    │
    └─► YES: → STAGING
        Then route to activity/entity/net from there
```

---

## Quick Classification Tests

### Test 1: The Timestamp Test
> "Does this data have a single, definitive `occurred_at` timestamp?"

| Answer | Classification |
|--------|----------------|
| YES - one event time | ACTIVITY |
| NO - has valid_from/valid_to | ENTITY (SCD) |
| NO - has period_start/period_end | NET |

### Test 2: The Mutation Test
> "If the underlying source changes, should we UPDATE or APPEND?"

| Answer | Classification |
|--------|----------------|
| APPEND new record | ACTIVITY |
| UPDATE existing record | ENTITY |
| RECALCULATE period | NET |

### Test 3: The Grain Test
> "What does ONE ROW represent?"

| One Row = | Classification |
|-----------|----------------|
| One event occurrence | ACTIVITY |
| One instance of a thing | ENTITY |
| One time period aggregation | NET |

### Test 4: The Primary Key Test
> "What uniquely identifies a record?"

| Primary Key Pattern | Classification |
|--------------------|----------------|
| `entity_id + occurred_at` | ACTIVITY |
| `entity_id` (natural or surrogate) | ENTITY |
| `entity_id + period_start` | NET |

---

## Common Scenarios

### Scenario 1: Orders
```
Q: Where does order data go?
A: BOTH - it splits:

ORDER PLACED (Activity)
- order_id, customer_id, occurred_at, order_total
- Immutable: captures the moment of placement
- Grain: one order placement event

ORDER (Entity)
- order_id, status, shipping_address, last_updated
- Mutable: status changes over time
- Grain: one order with current state
```

### Scenario 2: Subscriptions
```
Q: Where does subscription data go?
A: BOTH - it splits:

SUBSCRIPTION CHANGED (Activity)
- subscription_id, customer_id, occurred_at, old_plan, new_plan
- Immutable: captures each plan change
- Grain: one subscription change event

SUBSCRIPTION (Entity)
- subscription_id, current_plan, status, start_date
- Mutable: plan and status change
- Grain: one subscription with current state
```

### Scenario 3: User Logins
```
Q: Activity or Entity?
A: ACTIVITY only

USER LOGGED IN (Activity)
- user_id, occurred_at, device_type, ip_address
- Immutable: login events don't change
- Grain: one login event

No entity needed - user is a separate entity
```

### Scenario 4: Product Catalog
```
Q: Activity or Entity?
A: ENTITY only (with possible activity)

PRODUCT (Entity)
- product_id, name, price, category, is_active
- Mutable: price and attributes change
- Grain: one product

Optional: PRODUCT UPDATED (Activity)
- Only if you need to track change history
```

### Scenario 5: Daily Revenue
```
Q: Where does this go?
A: NET

DAILY REVENUE (Net)
- date, total_revenue, order_count
- Pre-computed from activities
- Grain: one day

Built FROM activities, not stored as activity
```

---

## Red Flags: You're in the Wrong Layer

### Signs You Put an Activity in Entity Layer
- ❌ Model has `updated_at` that changes frequently
- ❌ Using incremental merge strategy on "events"
- ❌ Primary key doesn't include a timestamp
- ❌ Same record appears multiple times with different values

### Signs You Put an Entity in Activity Layer
- ❌ Model has `valid_from` / `valid_to` columns
- ❌ Updates to source should update existing records
- ❌ You're storing "current state" in an append-only table
- ❌ Primary key is just an ID without timestamp

### Signs You Need a Net (Not Entity)
- ❌ Entity is just aggregating activities
- ❌ Columns are all metrics (counts, sums, averages)
- ❌ Primary key includes a time period
- ❌ You're doing GROUP BY date in an entity

---

## Decision Matrix

| Characteristic | Activity | Entity | Net |
|----------------|----------|--------|-----|
| **Mutability** | Immutable | Mutable | Recalculated |
| **Time Reference** | occurred_at | valid_from/to | period_start/end |
| **Incremental Strategy** | Append | Merge | Delete+Insert |
| **Typical Verb** | happened, occurred | is, has | aggregated, computed |
| **Change Handling** | New row | Update row | Recalculate period |
| **Example Query** | "What happened?" | "What is it now?" | "What's the total?" |

---

## When Still Unsure

If the decision tree doesn't give a clear answer:

1. **Ask**: "Would a business user call this an EVENT or a THING?"
2. **Check**: Does similar data exist elsewhere in the project?
3. **Default**: When truly ambiguous, prefer ACTIVITY
   - Activities can always be aggregated into entities/nets
   - You can't disaggregate entities back into activities
4. **Escalate**: Consult data-architect for architectural decisions

---

## SOMA Layer Rules (Quick Reference)

```
STAGING → ACTIVITIES → ENTITIES → NETS
   ↓           ↓            ↓         ↓
 Clean     Events      Things    Metrics
 Rename    Immutable   Mutable   Pre-computed
```

**Allowed Dependencies**:
- Staging → Sources only
- Activities → Staging only
- Entities → Staging, Activities
- Nets → Activities, Entities

**Never**:
- Entities referencing Nets
- Activities referencing Entities
- Circular dependencies

---

## Memory Integration

### Before Layer Placement

Check existing patterns:

1. **Review past decisions**: `.claude/memory/reflections/architecture/`
   - "How did we classify similar data before?"
   - "What layer placement issues have we encountered?"

2. **Check project models**:
   ```bash
   # Find similar models by name pattern
   ls models/staging/  # Staging models
   ls models/activities/  # Activity models
   ls models/entities/  # Entity models (fct_, dim_)
   ls models/nets/  # Net models
   ```

### When Still Uncertain: Escalation Path

```
Uncertain about classification
       │
       ├─► Check memory for similar past decisions
       │
       ├─► Apply Quick Classification Tests (above)
       │
       ├─► Default to ACTIVITY if truly ambiguous
       │   (Can always aggregate later)
       │
       └─► Escalate to data-architect agent
           for architectural guidance
```

### Project-Specific Examples

**Activities in this project:**
- `act_transaction_posted` - Financial events
- `act_subscription_changed` - Plan changes
- `act_user_logged_in` - Login events

**Entities in this project:**
- `fct_subscriptions` - Subscription records
- `dim_customers` - Customer dimension
- `dim_products` - Product dimension

**Nets in this project:**
- `net_mrr_metrics` - Monthly MRR aggregations
- `net_customer_acquisition` - Acquisition metrics

### After Making Decision

If you encounter a new pattern, document it:

```markdown
// Add to .claude/memory/reflections/architecture/
## Layer Decision - [Model Name]

**Date:** YYYY-MM-DD
**Data Type:** [Description]
**Classification:** [Activity/Entity/Net]
**Reasoning:** [Why this layer]
**Tests Applied:** [Which classification tests]
```

This helps future decisions for similar data types.
