# Agent Teams Test Scenarios

## Purpose

These test scenarios verify that Agent Teams migration successfully replaces the hook-based orchestration system. Each scenario tests critical workflow patterns to ensure task dependencies, teammate coordination, and workflow chains function correctly.

**Run these scenarios during**:
- Week 2: Dual mode testing (compare hook vs Agent Teams outcomes)
- Week 3: After removing `pre-tool-use.py` and `subagent-stop.py`
- Week 4: Final validation before declaring migration complete

---

## Test Scenario 1: Simple Feature Implementation

**Purpose**: Verify basic linear workflow (architect → engineer → reviewer)

### Setup

**User Request**: "Add staging model for Salesforce opportunities"

**Expected Agent Teams Workflow**:
```
data-architect spawned
  ↓ completes design, creates task
dbt-engineer implements (depends on design task)
  ↓ completes implementation, creates task
dbt-code-reviewer reviews (depends on implementation task)
  ↓ approves (🟢)
Workflow COMPLETE
```

### Execution Steps

1. **Invoke**: "Add staging model for Salesforce opportunities using the feature-development team."

2. **Expected Behavior**:
   - Lead spawns data-architect teammate
   - Architect designs `stg_salesforce__opportunities`
   - Architect marks design task COMPLETE
   - Architect creates implementation task for dbt-engineer
   - Engineer task unblocks automatically (dependency satisfied)
   - Engineer implements model + schema.yml
   - Engineer marks implementation task COMPLETE
   - Engineer creates code review task for dbt-code-reviewer
   - Reviewer task unblocks automatically
   - Reviewer reviews and approves (🟢)
   - Reviewer marks review task COMPLETE with "✅ APPROVED"
   - **No new tasks created** - workflow complete

3. **Verify**:
   - [ ] All tasks completed in correct order
   - [ ] Task dependencies worked (no manual intervention)
   - [ ] Model builds successfully (`dbt build --select stg_salesforce__opportunities`)
   - [ ] All tests pass
   - [ ] Documentation complete (grain + PK)

### Success Criteria

- ✅ All 3 tasks (design, implement, review) completed
- ✅ No manual "invoke next agent" needed
- ✅ dbt build successful
- ✅ Tests passing
- ✅ Review approved (🟢)

**Pass/Fail**: ________

**Notes**: ___________________________________________________________

---

## Test Scenario 2: Review Feedback Loop

**Purpose**: Verify reviewer can create fix tasks and re-review automatically

### Setup

**User Request**: "Implement fct_customer_orders with intentional quality issues"

**Inject Quality Issues**:
- Missing PK tests
- Unsafe division (no NULLIF)
- No documentation

**Expected Agent Teams Workflow**:
```
dbt-engineer implements (with issues)
  ↓ creates review task
dbt-code-reviewer reviews → finds issues (🟡)
  ↓ creates fix task + re-review task
dbt-engineer fixes issues (depends on review task)
  ↓ marks fix task COMPLETE
dbt-code-reviewer re-reviews (depends on fix task)
  ↓ approves (🟢)
Workflow COMPLETE
```

### Execution Steps

1. **Invoke**: "Implement fct_customer_orders (intentionally skip PK tests and docs for testing)"

2. **Expected Behavior**:
   - Engineer implements with issues
   - Engineer creates review task
   - Reviewer finds 3 issues (🟡 score 65/100)
   - Reviewer marks review task COMPLETE
   - Reviewer creates fix task: "Fix: fct_customer_orders - Add PK tests, docs, safe division"
   - Reviewer creates re-review task: "Re-review fct_customer_orders after fixes" (depends on fix task)
   - Fix task unblocks automatically
   - Engineer applies fixes from auto-fix code
   - Engineer marks fix task COMPLETE
   - Re-review task unblocks automatically
   - Reviewer re-reviews and approves (🟢)
   - Reviewer marks re-review task COMPLETE
   - **No new tasks** - workflow complete

3. **Verify**:
   - [ ] Reviewer creates fix task with specific issues
   - [ ] Reviewer creates re-review task with dependency
   - [ ] Engineer applies all fixes
   - [ ] Re-review happens automatically (no manual trigger)
   - [ ] Loop terminates on approval

### Success Criteria

- ✅ Reviewer creates fix task + re-review task
- ✅ Engineer addresses all issues (PK tests, docs, safe division)
- ✅ Re-review task unblocks automatically after fix
- ✅ Final approval (🟢) terminates loop
- ✅ dbt build + tests pass after fixes

**Pass/Fail**: ________

**Notes**: ___________________________________________________________

---

## Test Scenario 3: Impact Analysis (DANGEROUS Classification)

**Purpose**: Verify impact-analyzer blocks dangerous changes and escalates to LEAD

### Setup

**User Request**: "Change branch_type 'RETAIL' to 'RETAIL_STORE' in account_metadata seed"

**Existing Downstream Usage** (create test scenario):
- `fct_revenue` has `WHERE branch_type = 'RETAIL'` (hard dependency)
- `met_branch_summary` has `CASE WHEN branch_type = 'RETAIL' THEN ...`

**Expected Agent Teams Workflow**:
```
impact-analyzer analyzes change
  ↓ 5-gate analysis detects DANGEROUS
  ↓ creates escalation task for LEAD (not implementation task)
LEAD reviews dangerous impact
  ↓ decides: approve alternative, modify scope, or cancel
```

### Execution Steps

1. **Setup Test Data**:
   - Ensure `fct_revenue` has `WHERE branch_type = 'RETAIL'`
   - Ensure `met_branch_summary` has `CASE WHEN branch_type = 'RETAIL'`

2. **Invoke**: "Change branch_type 'RETAIL' to 'RETAIL_STORE' in account_metadata"

3. **Expected Behavior**:
   - Lead spawns impact-analyzer
   - Analyzer executes 5-gate analysis:
     - Gate 1: Mutative change (high risk)
     - Gate 2: Traces downstream (finds fct_revenue, met_branch_summary)
     - Gate 3: Detects HARD dependencies (WHERE = 'RETAIL', CASE WHEN 'RETAIL')
     - Gate 4: Checks dimension collisions
     - Gate 5: Classifies as **DANGEROUS** (data loss risk)
   - Analyzer marks task COMPLETE with "⛔ DANGEROUS" classification
   - Analyzer creates escalation task for LEAD: "⛔ DANGEROUS CHANGE BLOCKED: Change branch_type RETAIL"
   - Analyzer provides alternative approach (additive: add 'RETAIL_STORE', keep 'RETAIL')
   - Analyzer **DOES NOT create implementation task** for original change
   - Lead reviews escalation
   - User decides: approve alternative or cancel

4. **Verify**:
   - [ ] Analyzer correctly identifies DANGEROUS
   - [ ] No implementation task created for original change
   - [ ] Escalation task created for LEAD
   - [ ] Alternative approach provided (additive)
   - [ ] Original change blocked

### Success Criteria

- ✅ Analyzer classifies as DANGEROUS
- ✅ Hard dependencies detected (WHERE, CASE WHEN)
- ✅ No implementation task created
- ✅ LEAD escalation task created with alternative
- ✅ User must explicitly approve before proceeding

**Pass/Fail**: ________

**Notes**: ___________________________________________________________

---

## Test Scenario 4: Metrics Definition + Validation

**Purpose**: Verify metrics-analyst can define metric, trigger implementation, and validate

### Setup

**User Request**: "Define Net Revenue Retention (NRR) metric"

**Expected Agent Teams Workflow**:
```
metrics-analyst defines NRR
  ↓ creates implementation task + validation task
dbt-engineer implements met_nrr (depends on definition)
  ↓ creates review task
dbt-code-reviewer reviews (depends on implementation)
  ↓ approves
metrics-analyst validates calculation (depends on implementation)
  ↓ reconciles with source
  ↓ IF matches → COMPLETE
  ↓ IF discrepancy → creates fix task → loop
```

### Execution Steps

1. **Invoke**: "Define Net Revenue Retention metric using the metrics-team"

2. **Expected Behavior**:
   - Lead spawns metrics-analyst
   - Analyst defines NRR as compound metric:
     - Formula: `(Starting ARR + Expansion - Contraction - Churn) / Starting ARR`
     - Type: Compound (4 components)
     - Category: Growth
   - Analyst marks definition task COMPLETE
   - Analyst creates implementation task for dbt-engineer
   - Analyst creates validation task for self (depends on implementation)
   - Engineer implements `met_nrr` model
   - Engineer creates review task
   - Reviewer approves
   - Validation task unblocks
   - Analyst runs validation query and compares to expected value
   - IF matches → Marks validation task COMPLETE
   - IF discrepancy → Creates fix task → Loop

3. **Verify**:
   - [ ] Metric defined with business context and formula
   - [ ] Implementation task created for engineer
   - [ ] Validation task created for analyst (depends on implementation)
   - [ ] Engineer implements model correctly
   - [ ] Validation confirms calculation matches definition

### Success Criteria

- ✅ Metric definition complete (formula, type, category)
- ✅ Implementation task created with full spec
- ✅ Validation task created with dependency
- ✅ Model built successfully
- ✅ Validation confirms correctness (matches expected value within tolerance)

**Pass/Fail**: ________

**Notes**: ___________________________________________________________

---

## Test Scenario 5: Performance Optimization

**Purpose**: Verify performance-optimizer can diagnose, recommend, and A/B test

### Setup

**User Request**: "Optimize fct_orders - it's taking 8 minutes to build"

**Create Slow Query** (if needed):
- Ensure fct_orders has no clustering
- Ensure full table scan occurs

**Expected Agent Teams Workflow**:
```
performance-optimizer diagnoses slow query
  ↓ creates implementation task (add clustering)
  ↓ creates A/B test task for self (depends on implementation)
dbt-engineer adds clustering config (depends on analysis)
  ↓ creates review task
dbt-code-reviewer reviews config (depends on implementation)
  ↓ approves
performance-optimizer runs A/B test (depends on implementation)
  ↓ measures before/after
  ↓ IF improvement ≥target → documents baseline → COMPLETE
  ↓ IF < target → creates alternative optimization → loop
```

### Execution Steps

1. **Invoke**: "fct_orders is too slow, use performance-team"

2. **Expected Behavior**:
   - Lead spawns performance-optimizer
   - Optimizer diagnoses using Snowflake query history:
     - Execution time: 8 minutes
     - Partitions scanned: 100% (full table scan)
     - Root cause: No clustering, full table scan on filtered column
   - Optimizer marks analysis task COMPLETE with baseline metrics
   - Optimizer creates implementation task: "Add clustering to fct_orders on order_date, customer_id"
   - Optimizer creates A/B test task for self (depends on implementation)
   - Engineer adds clustering config
   - Engineer creates review task
   - Reviewer approves config
   - A/B test task unblocks
   - Optimizer runs optimized query and measures:
     - Execution time: 1.5 minutes (5.3x faster)
     - Partitions scanned: 15% (significant reduction)
     - Cost reduced by 60%
   - Optimizer documents baseline in Letta with tags ["baseline", "model:fct_orders"]
   - Optimizer marks A/B test task COMPLETE
   - Workflow complete

3. **Verify**:
   - [ ] Diagnosis identifies root cause (full table scan)
   - [ ] Baseline metrics captured
   - [ ] Optimization implemented (clustering config)
   - [ ] A/B test shows improvement (≥50% faster)
   - [ ] Baseline documented in memory

### Success Criteria

- ✅ Root cause identified (no clustering)
- ✅ Baseline metrics documented
- ✅ Optimization implemented
- ✅ A/B test shows ≥50% improvement
- ✅ Results stored in Letta with tag "baseline"

**Pass/Fail**: ________

**Notes**: ___________________________________________________________

---

## Verification Checklist

After running all 5 test scenarios, verify:

| Category | Check | Pass/Fail |
|----------|-------|-----------|
| **Functionality** | All 5 test workflows completed successfully | |
| **Task Dependencies** | Tasks unblocked automatically when dependencies satisfied | |
| **Teammate Coordination** | Teammates created follow-up tasks per spawn prompts | |
| **Safety Gates** | Impact analyzer blocked DANGEROUS change (Test 3) | |
| **Review Loops** | Feedback loop completed without manual intervention (Test 2) | |
| **Memory** | session-start.py still injects context | |
| **Memory** | post-tool-use.py still tracks builds | |
| **Memory** | session-stop.py still triggers retrospectives | |
| **Performance** | Token usage < 4x equivalent single session | |
| **Documentation** | CLAUDE.md reflects new patterns | |
| **Rollback** | Archived hooks can be restored | |

**Minimum passing**: 10/11 checks (allow 1 minor issue for post-migration fix)

**Overall Result**: ________

**Migration Status**: ☐ Ready to remove hooks ☐ Needs more testing ☐ Rollback required

---

## Troubleshooting

### Issue: Task dependencies not working

**Symptoms**:
- Dependent tasks don't start automatically
- Manual "invoke next agent" needed

**Check**:
1. Did teammate set dependency correctly?
2. Is CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS still set to "1"?
3. Did teammate mark their task COMPLETE?

**Fix**: Verify settings.json, check task completion, ensure dependency IDs are valid

---

### Issue: Teammate creates wrong task type

**Symptoms**:
- Engineer doesn't create review task
- Reviewer doesn't create fix task when issues found

**Check**:
1. Read teammate's spawn prompt - are scenarios clear?
2. Did teammate read the correct spawn prompt?
3. Is outcome classification correct (🟢/🟡/🔴)?

**Fix**: Clarify spawn prompt scenarios, ensure teammates reference correct prompts

---

### Issue: Workflow doesn't terminate

**Symptoms**:
- Review loop continues indefinitely
- Tasks keep creating more tasks

**Check**:
1. Is there a termination condition (🟢 approval)?
2. Are max iterations enforced (3 review cycles)?
3. Is escalation to LEAD defined?

**Fix**: Add max iteration limits to spawn prompts, define escalation paths

---

## Post-Test Actions

### If Tests Pass (10/11 checks)

1. **Week 3**: Remove `pre-tool-use.py` hook
   - Edit `.claude/settings.json` to remove PreToolUse
   - Test routing still works (lead assigns correctly)

2. **Week 3**: Remove `subagent-stop.py` hook
   - Edit `.claude/settings.json` to remove SubagentStop
   - Test workflow chains still work (task dependencies)

3. **Week 4**: Run all tests again in final configuration
   - Verify all tests still pass without hooks
   - Complete verification checklist

4. **Declare migration complete**
   - Document in changelog
   - Archive hooks permanently
   - Update status in migration-plan.md

### If Tests Fail (< 10/11 checks)

1. **Document failures** in `.claude/teams/migration-issues.md`
   - What failed
   - Why it failed
   - What needs fixing

2. **Rollback** if critical failures:
   ```bash
   # Disable Agent Teams
   # Edit .claude/settings.json: Set CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS="0"

   # Restore hooks
   cp .claude/hooks/archive/hook-based-orchestration/*.py .claude/hooks/

   # Revert config
   git checkout HEAD -- .claude/settings.json CLAUDE.md
   ```

3. **Fix issues** before retrying:
   - Update spawn prompts
   - Clarify task creation rules
   - Add missing scenarios

4. **Re-run tests** after fixes

---

## Test Log

| Date | Tester | Phase | Tests Passed | Tests Failed | Notes |
|------|--------|-------|--------------|--------------|-------|
| | | Dual Mode | /5 | /5 | |
| | | After Hook Removal | /5 | /5 | |
| | | Final Validation | /5 | /5 | |

**Migration Decision**: ☐ APPROVED ☐ NEEDS WORK ☐ ROLLBACK

**Signed**: _______________ **Date**: ___________