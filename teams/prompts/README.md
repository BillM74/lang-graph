# Teammate Spawn Prompts

This directory contains spawn prompts for Agent Teams teammates. Each prompt defines:

1. **Role and responsibilities** of the teammate
2. **Task creation rules** for different scenarios
3. **Workflow patterns** for coordination
4. **Success criteria** and quality standards

---

## Available Spawn Prompts

### Implementation & Build

| Teammate | File | When to Spawn | What They Create |
|----------|------|---------------|------------------|
| **data-architect** | [data-architect.md](data-architect.md) | Schema design, SOMA layer decisions | Implementation tasks for dbt-engineer |
| **dbt-engineer** | [dbt-engineer.md](dbt-engineer.md) | Model implementation, SQL development | Code review tasks for dbt-code-reviewer |
| **dbt-code-reviewer** | [dbt-code-reviewer.md](dbt-code-reviewer.md) | Code review, quality validation | Fix tasks for dbt-engineer (if issues found) |

### Specialized Analysis

| Teammate | File | When to Spawn | What They Create |
|----------|------|---------------|------------------|
| **impact-analyzer** | [impact-analyzer.md](impact-analyzer.md) | Before modifying seeds/sources/dimensions | Implementation tasks (if SAFE) or escalations (if DANGEROUS) |
| **metrics-analyst** | [metrics-analyst.md](metrics-analyst.md) | Metric definitions, validation | Implementation tasks for dbt-engineer, validation tasks for self |
| **performance-optimizer** | [performance-optimizer.md](performance-optimizer.md) | Slow queries, high costs | Implementation tasks for dbt-engineer, A/B test tasks for self |

### Orchestration & Learning

| Teammate | File | When to Spawn | What They Create |
|----------|------|---------------|------------------|
| **project-manager** | [project-manager.md](project-manager.md) | Multi-feature projects (5+ models) | Milestone tasks, subtasks for all agents |
| **retrospective-analyst** | [retrospective-analyst.md](retrospective-analyst.md) | After completed workflows | Nothing (terminal - writes to memory only) |

---

## How Spawn Prompts Work

### 1. Teammate Reads Spawn Prompt

When a teammate is spawned, they automatically load their spawn prompt which contains:

- Full role description
- Reference to detailed agent definition (`.claude/agents/*.md`)
- Skills available
- Task creation rules based on outcomes

### 2. Teammate Completes Work

Teammate follows their agent definition process (e.g., 5-gate analysis for impact-analyzer, quality rubric for dbt-code-reviewer).

### 3. Teammate Creates Follow-Up Tasks

Based on the outcome, teammate creates tasks per spawn prompt scenarios:

**Example** (from `dbt-code-reviewer.md`):
- **Scenario 1** (🟢 Approved): Mark task COMPLETE, no new tasks
- **Scenario 2** (🟡 Changes): Create fix task for engineer + re-review task for self
- **Scenario 3** (🔴 Rework): Create escalation task for LEAD

### 4. Task Dependencies Unblock Workflow

Tasks with dependencies automatically start when prerequisites complete. No manual handoffs needed.

---

## Spawn Prompt Structure

Each prompt follows this standard format:

```markdown
# [Teammate Name] - Agent Teams Spawn Prompt

## Role
[Brief description]
[Reference to agent definition]
[Skills available]

## Your Task
[What teammate should do]

## Task Creation Rules for Agent Teams

### Scenario 1: [Outcome A]
**When**: [Condition]
**Actions**:
1. Mark your task as COMPLETE with [notes]
2. Create task: [Description] for [agent]

### Scenario 2: [Outcome B]
...

## [Additional Sections]
- Templates
- Quality rubrics
- Important notes
- Success criteria
```

---

## Task Creation Best Practices

### For Teammates

**DO**:
- ✅ Always mark your task COMPLETE when done
- ✅ Include structured completion notes (context for next agent)
- ✅ Set correct dependencies (tasks unblock automatically)
- ✅ Assign to correct agent (use role names like dbt-engineer)
- ✅ Provide full context (next agent shouldn't need to ask)

**DON'T**:
- ❌ Create tasks without dependencies (creates orphans)
- ❌ Assume next agent has context (include everything)
- ❌ Create circular dependencies (escalate to LEAD instead)
- ❌ Skip completion notes (next agent needs your findings)

### Example Good Task

```
Title: "Fix: fct_orders - Add missing PK tests"
Assigned to: dbt-engineer
Depends on: [review task ID]
Priority: High

Description:
Code review identified missing PK tests.

**🔴 BLOCKING Issues**:
1. Missing unique + not_null tests on order_id [Line 1]
   **Auto-Fix**:
   ```yaml
   - name: order_id
     data_tests:
       - unique
       - not_null
   ```

**Context**:
- Model: models/activities/fct_orders.sql
- Schema: models/activities/schema.yml
- Review score: 65/100 (Testing: 4/10 - needs improvement)

See full review in: [link to review task]
```

**Why this is good**:
- Clear title with model name
- Dependency set (unblocks automatically when review completes)
- Auto-fix code provided (engineer can copy-paste)
- Context included (engineer knows where to look)
- Reference to full review (for details)

---

## Workflow Coordination Patterns

### Pattern 1: Linear Chain (Sequential)

```
Task A (architect design)
  ↓ depends on A
Task B (engineer implement)
  ↓ depends on B
Task C (reviewer review)
```

Each task creates the next with dependency. No manual intervention.

### Pattern 2: Feedback Loop (Conditional)

```
Task A (engineer implement)
  ↓ depends on A
Task B (reviewer review)
  ↓ IF issues (creates Task C)
Task C (engineer fix) → depends on B
  ↓ (creates Task D)
Task D (reviewer re-review) → depends on C
  ↓ IF approved → COMPLETE
```

Reviewer creates fix + re-review tasks. Loop continues until approved.

### Pattern 3: Conditional Branch (Safety Gate)

```
Task A (analyzer analyze change)
  ↓ depends on A
IF SAFE:
  Task B (engineer implement)
IF CAUTION:
  Task B (LEAD review) → User decides
IF DANGEROUS:
  Task B (LEAD escalation) → Original change BLOCKED
```

Analyzer creates different tasks based on classification. Prevents unsafe changes.

### Pattern 4: Parallel Work (Independent)

```
Task A (architect design)
  ↓ depends on A (both)
Task B (engineer implement dim_customers) ║ Task C (engineer implement dim_products)
  ↓ depends on B                          ║   ↓ depends on C
Task D (reviewer review customers)        ║ Task E (reviewer review products)
```

Multiple tasks can run simultaneously if no dependencies between them.

---

## Customizing Spawn Prompts

### When to Modify

Modify spawn prompts when:
- Process improvements identified (via retrospective-analyst)
- New workflow patterns emerge
- Task creation rules need refinement
- Quality thresholds need adjustment

### How to Modify

1. Edit the spawn prompt markdown file
2. Update task creation scenarios
3. Document change in git commit
4. Test with representative workflow
5. Update this README if adding new patterns

**Migration-safe**: Changes to spawn prompts don't require rollback - teammates read them fresh each spawn.

---

## Troubleshooting

### Issue: Teammate creates wrong task type

**Check**:
1. Is spawn prompt clear about which scenario applies?
2. Are conditions well-defined?
3. Does teammate have correct outcome information?

**Fix**: Clarify scenario triggers in spawn prompt

---

### Issue: Task dependency chain breaks

**Check**:
1. Did teammate mark their task COMPLETE?
2. Did teammate set dependency correctly?
3. Is dependency task ID valid?

**Fix**: Ensure teammates always set dependencies and mark tasks COMPLETE

---

### Issue: Circular dependencies created

**Check**:
1. Are two teammates creating tasks for each other without termination?
2. Is there an escalation path to LEAD?

**Fix**: Add escalation scenarios to spawn prompts (max iterations, LEAD involvement)

---

## References

- **Agent Teams Docs**: https://code.claude.com/docs/en/agent-teams
- **Agent Definitions**: `.claude/agents/*.md` (detailed processes)
- **Migration Plan**: `.claude/teams/migration-plan.md` (context)
- **Test Scenarios**: `.claude/teams/test-scenarios.md` (verification workflows)

---

## Changelog

- **2026-02-13**: Initial spawn prompts created for Agent Teams migration
  - 8 teammates: data-architect, dbt-engineer, dbt-code-reviewer, impact-analyzer, metrics-analyst, performance-optimizer, retrospective-analyst, project-manager
  - Task creation rules defined for each scenario
  - Workflow coordination patterns documented
