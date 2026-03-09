---
name: code-review-feedback
description: Code review feedback patterns and communication style. Use when: "provide feedback", "review comments", "how to give feedback", "code review style", "constructive feedback", "review tone", "feedback template", "review response"
---

# Code Review Feedback Guide

Standards for providing constructive, actionable code review feedback.

## Feedback Categories

Use these categories to prioritize feedback:

### Blocking Issues (Must Fix)

Issues that must be resolved before merging.

**Format:**
```
🔴 **BLOCKING** [file:line] Issue description
   **Why:** Explanation of the problem
   **Fix:** Suggested solution
```

**Examples:**
- Missing primary key test
- SQL injection vulnerability
- Incorrect business logic
- Breaking change without migration
- Missing required documentation

### Suggestions (Should Consider)

Recommended improvements that would enhance quality.

**Format:**
```
🟡 **SUGGESTION** [file:line] Improvement description
   **Why:** Benefit of the change
   **Example:** Code example if helpful
```

**Examples:**
- Performance optimization opportunity
- Code style improvement
- Better naming suggestion
- Additional test coverage
- Documentation enhancement

### Questions (Clarification)

Points requiring clarification or discussion.

**Format:**
```
🔵 **QUESTION** [file:line] Question about approach
   **Context:** What I'm trying to understand
```

**Examples:**
- Why was this approach chosen?
- Is this intentional behavior?
- How does this handle edge case X?
- What's the expected behavior when Y?

### Praise (Good Patterns)

Highlight good practices to reinforce them.

**Format:**
```
✅ **GOOD** [file:line] What was done well
   **Why:** Why this is a good practice
```

**Examples:**
- Clean CTE structure
- Comprehensive test coverage
- Clear documentation
- Efficient query pattern
- Proper error handling

---

## Feedback Principles

### Be Specific and Actionable

```
-- Bad feedback:
"This could be better"

-- Good feedback:
🟡 **SUGGESTION** [fct_orders.sql:45] Consider using QUALIFY instead of subquery
   **Why:** QUALIFY is more readable and often more performant in Snowflake
   **Example:**
   ```sql
   -- Current
   select * from (
       select *, row_number() over (...) as rn
       from orders
   ) where rn = 1

   -- Suggested
   select *
   from orders
   qualify row_number() over (...) = 1
   ```
```

### Explain the "Why"

```
-- Bad feedback:
"Add a not_null test here"

-- Good feedback:
🔴 **BLOCKING** [schema.yml:23] Primary key `order_id` needs not_null test
   **Why:** Without not_null, duplicate records with NULL keys won't be caught,
   leading to incorrect aggregations downstream
   **Fix:** Add `- not_null` alongside the unique test
```

### Offer Solutions, Not Just Problems

```
-- Bad feedback:
"This join is inefficient"

-- Good feedback:
🟡 **SUGGESTION** [fct_orders.sql:78] Pre-filter before joining for better performance
   **Why:** Filtering 1M rows before joining is faster than joining then filtering
   **Current:**
   select * from orders o
   left join customers c on o.customer_id = c.customer_id
   where o.order_date >= '2024-01-01'

   **Suggested:**
   with filtered_orders as (
       select * from orders where order_date >= '2024-01-01'
   )
   select * from filtered_orders o
   left join customers c on o.customer_id = c.customer_id
```

### Use Questions for Subjective Issues

```
-- Instead of:
"You should use a different approach here"

-- Use:
🔵 **QUESTION** [int_orders.sql:34] I see you're using a subquery here.
   Was there a specific reason for this over a CTE?
   **Context:** CTEs are our standard pattern, curious if there's a
   performance consideration I'm missing.
```

---

## Review Response Template

Use this structure for comprehensive PR reviews:

```markdown
## PR Review: [PR Title]

### Summary
[1-2 sentences about what this PR accomplishes]

### Overall Assessment
- [ ] Approve
- [ ] Request Changes
- [ ] Comment Only

### SOMA Compliance
- [x] Layer flow correct (staging → activities → entities → nets)
- [x] Naming conventions followed
- [ ] ⚠️ Missing: [specific issue]

### Code Quality
- [x] SQL style consistent
- [x] CTE pattern followed
- [ ] ⚠️ Issue: [specific issue]

### Testing
- [x] Primary key tested
- [ ] ⚠️ Missing: [specific test]

### Documentation
- [x] Model documented
- [ ] ⚠️ Missing: [specific docs]

---

### Blocking Issues
1. 🔴 [file:line] Issue description

### Suggestions
1. 🟡 [file:line] Suggestion description

### Questions
1. 🔵 [file:line] Question

### Good Patterns
1. ✅ [file:line] What was done well
```

---

## Common Feedback Scenarios

### Missing Tests

```
🔴 **BLOCKING** [_schema.yml] Missing required tests on `fct_orders`

**Required tests:**
- Primary key (`order_id`): unique + not_null
- Foreign key (`customer_id`): not_null + relationships
- Status column: accepted_values

**Fix:** Add to schema.yml:
```yaml
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
```
```

### SQL Style Issues

```
🟡 **SUGGESTION** [fct_orders.sql:12-25] SQL formatting inconsistent

**Issues found:**
- Mixed case keywords (SELECT vs select)
- Leading commas (we use trailing)
- Inconsistent indentation

**Reference:** See sql-code-quality skill for our standards
```

### Performance Concern

```
🟡 **SUGGESTION** [fct_large_table.sql] Consider incremental materialization

**Current:** Table materialization rebuilds 50M+ rows daily
**Suggested:** Incremental with merge strategy

**Why:** Would reduce build time from ~30 min to ~5 min

**Example config:**
```sql
{{
    config(
        materialized='incremental',
        incremental_strategy='merge',
        unique_key='record_id'
    )
}}
```
```

### SOMA Violation

```
🔴 **BLOCKING** [net_metrics.sql:5] SOMA layer violation

**Issue:** Net model directly references staging (`stg_orders`)
**Rule:** Nets should only reference entities (fct_/dim_) or other nets

**Current flow:** stg_orders → net_metrics (VIOLATION)
**Correct flow:** stg_orders → fct_orders → net_metrics

**Fix:** Reference `fct_orders` instead of `stg_orders`
```

---

## Tone Guidelines

### Do

- Be respectful and professional
- Assume good intent
- Focus on the code, not the person
- Acknowledge what's done well
- Be concise but complete
- Offer to pair on complex issues

### Don't

- Use condescending language ("obviously", "simply", "just")
- Make it personal ("you always...", "you should know...")
- Be vague ("this is wrong")
- Only point out negatives
- Demand changes without explanation
- Use absolutes ("never do this")

### Phrases to Use

```
"Have you considered..."
"One approach could be..."
"I wonder if..."
"Nice use of..."
"Could you help me understand..."
"What do you think about..."
```

### Phrases to Avoid

```
"Why didn't you..."
"You should have..."
"This is wrong"
"Obviously..."
"I don't understand why you..."
"This doesn't make sense"
```

---

## Memory Integration

### Before Providing Feedback

Check past review patterns:

1. **Review past feedback**: `.claude/memory/reflections/reviews/`
   - "What feedback has been well-received?"
   - "What suggestions have led to improvements?"

2. **Check issue frequency**:
   - If issue is common, have a standard response ready
   - Reference past fixes as examples

### Auto-Fix Suggestions

For common issues, provide exact fix code:

#### Missing Primary Key Test
```markdown
🔴 **BLOCKING** [schema.yml] Missing PK test on `order_id`

**Fix:** Add to schema.yml:
```yaml
columns:
  - name: order_id
    tests:
      - unique
      - not_null
```
```

#### Division Without NULLIF
```markdown
🔴 **BLOCKING** [model.sql:45] Unprotected division

**Current:**
```sql
revenue / customers as arpu
```

**Fix:**
```sql
revenue / nullif(customers, 0) as arpu
```
```

#### Missing Incremental Logic
```markdown
🟡 **SUGGESTION** [model.sql] Consider adding incremental logic

**Fix:**
```sql
{% if is_incremental() %}
    where updated_at > (select max(updated_at) from {{ this }})
{% endif %}
```
```

### After Providing Feedback

**Track feedback outcomes:**

1. **Store in memory**: `.claude/memory/reflections/reviews/`
   ```markdown
   ## Feedback Given - [PR/Model]

   **Date:** YYYY-MM-DD
   **Feedback Type:** Blocking/Suggestion

   **Issue:** [Description]
   **Feedback Given:** [What was said]
   **Outcome:** [Accepted/Rejected/Modified]

   **Learning:**
   - [Was feedback well-received?]
   - [Should adjust approach?]
   ```

2. **Calibrate severity**: If a "blocking" issue is often dismissed, consider downgrading to "suggestion"

### Feedback Effectiveness Tracking

| Feedback Type | Acceptance Rate | Adjust If |
|---------------|-----------------|-----------|
| Blocking - Tests | 95%+ expected | < 90%: review criteria |
| Blocking - Security | 100% expected | Any rejection: escalate |
| Suggestions | 60-80% expected | < 50%: reconsider value |
| Questions | N/A | Low response: clarify ask |