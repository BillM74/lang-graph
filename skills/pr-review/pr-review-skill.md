---
name: pr-review
description: Standardized pull request review workflow for dbt and analytics code. Use when: "review my changes", "check this PR", "code review", "review this", "PR review", "validate code", "check code quality", "review pull request", "look at this change"
compatibility: Requires dbt-mcp and snowflake-mcp servers
---

# PR Review Workflow

Follow this systematic review process for all pull requests in the analytics project.

## MCP Tools for Review

This skill leverages MCP tools for automated validation:

| Task | MCP Tool | Usage |
|------|----------|-------|
| Check model lineage | `mcp__dbt__get_model_lineage_dev` | See upstream/downstream impact |
| Run changed models | `mcp__dbt__build` | Build with selector `<model>+` |
| Test models | `mcp__dbt__test` | Run tests on changed models |
| Preview output | `mcp__dbt__show` | Validate SQL, see sample data |
| List affected models | `mcp__dbt__list` | Find models matching patterns |
| Query Snowflake | `mcp__snowflake__run_snowflake_query` | Validate data, check results |
| Describe tables | `mcp__snowflake__describe_object` | Verify schema changes |

### MCP-Powered Review Steps

1. **Check Lineage Impact**
   Use `mcp__dbt__get_model_lineage_dev` with:
   - `model_id`: the changed model name
   - `direction`: "both"
   - `recursive`: true

   This shows all upstream dependencies and downstream consumers.

2. **Preview Model Changes**
   Use `mcp__dbt__show` with the model's SQL to validate:
   - Query compiles correctly
   - Output looks reasonable
   - No obvious data issues

3. **Run Affected Models**
   Use `mcp__dbt__build` with selector `<model_name>+` to:
   - Run the changed model
   - Run all downstream models
   - Execute all associated tests

4. **Validate in Snowflake**
   Use `mcp__snowflake__run_snowflake_query` to:
   - Check row counts before/after
   - Validate metric calculations
   - Compare against expected values

---

## Review Checklist

### 1. Understand the Change

- [ ] Read PR description and linked issues
- [ ] Understand the business context
- [ ] Identify affected models and downstream dependencies

### 2. SOMA Compliance

- [ ] **Layer Flow**: Changes follow staging → activities → entities → nets flow
- [ ] **Naming**: Correct prefixes used (`stg_`, `act_`, `fct_`, `dim_`, `net_`)
- [ ] **Metrics**: Atomic metrics defined before compound metrics
- [ ] **Activities**: Include `activity_id`, `occurred_at`, and dimension columns
- [ ] **Nets**: Include bi-temporal columns (`measured_at`, `valid_from`, `valid_to`)

### 3. Code Quality

#### SQL Style
- [ ] 4-space indentation (no tabs)
- [ ] Lowercase keywords (`select`, `from`, `where`)
- [ ] One column per line in SELECT
- [ ] Trailing commas
- [ ] CTEs named clearly (imports → logic → final)

#### Patterns
- [ ] Safe division with `nullif()` protection
- [ ] Appropriate use of `{{ ref() }}` and `{{ source() }}`
- [ ] Surrogate keys using `dbt_utils.generate_surrogate_key()`
- [ ] No hardcoded dates or values
- [ ] Incremental models have proper `is_incremental()` logic

#### Structure
- [ ] Config block at top
- [ ] Import CTEs first
- [ ] Logical CTEs in middle
- [ ] Final CTE for output
- [ ] `SELECT * FROM final` at end

### 4. Testing Coverage

#### Required Tests
- [ ] **Primary Key**: `unique` + `not_null`
- [ ] **Foreign Keys**: `relationships` test
- [ ] **Categorical**: `accepted_values` for status/type columns
- [ ] **Business Rules**: Custom tests for domain logic

#### Data Quality
- [ ] Non-negative amounts where applicable
- [ ] Date ranges are valid
- [ ] Percentages between 0-100 (or 0-1)
- [ ] Freshness tests for source data

### 5. Documentation

- [ ] Model-level description with grain
- [ ] All columns documented
- [ ] Primary key identified
- [ ] Foreign keys explained
- [ ] Calculated fields have formulas
- [ ] Caveats noted

### 6. Performance

- [ ] Appropriate materialization (`view`, `table`, `incremental`)
- [ ] Incremental strategy for large tables
- [ ] Clustering keys for Snowflake (where beneficial)
- [ ] No unnecessary `SELECT *`
- [ ] Efficient join patterns

### 7. Security & Governance

- [ ] No PII exposed inappropriately
- [ ] Sensitive columns masked or excluded
- [ ] Access grants configured correctly
- [ ] No credentials in code

## Review Process

### Step 1: Get PR Details
```bash
# View PR changes
gh pr view <number> --web
# or
gh pr diff <number>
```

### Step 2: Run Local Validation
```bash
# Parse and compile
dbt parse
dbt compile --select <changed_models>

# Run changed models
dbt run --select <changed_models>

# Run tests
dbt test --select <changed_models>
```

### Step 3: Check Dependencies
```bash
# See what depends on changed models
dbt ls --select <model>+
```

### Step 4: Provide Feedback

Use this format for review comments:

**Blocking Issues** (must fix):
```
🚫 [File:Line] Issue description
   Suggestion: How to fix
```

**Suggestions** (recommended):
```
💡 [File:Line] Suggestion description
   Example: Code example
```

**Questions** (clarification needed):
```
❓ [File:Line] Question about intent or approach
```

**Praise** (good patterns):
```
✅ [File:Line] Good use of [pattern/practice]
```

## Common Issues to Flag

### SOMA Violations
- Nets referencing staging directly (skip layers)
- Missing bi-temporal columns in nets
- Compound metrics without atomic components
- Activities missing `occurred_at`

### Testing Gaps
- Primary key without unique+not_null
- Foreign keys without relationships test
- Status columns without accepted_values
- No freshness tests on sources

### SQL Anti-patterns
- `SELECT *` in non-final CTEs
- Division without nullif protection
- Hardcoded filter values
- Missing incremental logic for large tables

### Documentation Issues
- Model without description
- Undocumented columns
- Missing grain specification
- No test coverage explanation

## Review Response Template

```markdown
## PR Review: [PR Title]

### Summary
[1-2 sentences about what this PR does]

### SOMA Compliance
- [x] Layer flow correct
- [x] Naming conventions followed
- [ ] Missing: [specific issue]

### Code Quality
- [x] SQL style consistent
- [x] CTE pattern followed
- [ ] Issue: [specific issue]

### Testing
- [x] Primary key tested
- [ ] Missing: [specific test]

### Documentation
- [x] Model documented
- [ ] Missing: [specific docs]

### Blocking Issues
1. [Issue requiring fix before merge]

### Suggestions
1. [Non-blocking improvement]

### Decision
- [ ] Approve
- [ ] Request Changes
- [ ] Comment Only
```

## Quick Commands

```bash
# View PR
gh pr view <number>

# Check out PR locally
gh pr checkout <number>

# Run affected models
dbt build --select state:modified+

# Approve PR
gh pr review <number> --approve

# Request changes
gh pr review <number> --request-changes --body "..."
```

---

## Memory Integration

### Before Reviewing

Query the memory system:

1. **Check review patterns**: `.claude/memory/reflections/reviews/`
   - "What issues have we commonly found in similar models?"
   - "What feedback patterns worked well?"

2. **Check common issues**: `.claude/memory/patterns/common-test-failures.json`
   - Look for patterns relevant to the changed models

### Pre-Review Automated Gates

Before starting manual review, verify automatically:

```bash
# 1. Parse and compile
dbt parse
dbt compile --select state:modified

# 2. Run changed models
dbt run --select state:modified

# 3. Run tests
dbt test --select state:modified

# 4. Check for SQL lint issues
sqlfluff lint models/ --select state:modified
```

If any of these fail, note in review that automated checks failed.

### After Reviewing

**Store learnings:**

1. **Record common issues found**: `.claude/memory/reflections/reviews/`
   ```markdown
   ## Review Reflection - [PR Title]

   **Date:** YYYY-MM-DD
   **PR:** #[number]

   **Issues Found:**
   - [Blocking issue 1]
   - [Suggestion 1]

   **Patterns Observed:**
   - [Recurring issue type]

   **What Worked Well:**
   - [Good patterns in the code]
   ```

2. **Update patterns if new issue type**: `.claude/memory/patterns/`

### Review Efficiency Tracking

Track to improve future reviews:

| Metric | Target |
|--------|--------|
| Issues caught before merge | 100% of blocking issues |
| False positives (wrong blocking issues) | < 5% |
| Review turnaround time | < 4 hours |
| Follow-up verification | All requested changes verified |

### Common Issues in This Project

Based on past reviews:

| Issue Type | Frequency | Auto-Detectable? |
|------------|-----------|------------------|
| Missing PK tests | High | Yes (via schema check) |
| Division without NULLIF | Medium | Yes (via grep) |
| SOMA layer violation | Medium | Partial (via naming) |
| Missing documentation | High | Yes (via schema check) |
| Incremental logic errors | Low | No (manual review) |
