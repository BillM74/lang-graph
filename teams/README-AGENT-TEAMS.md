# Agent Teams - SOMA Analytics Project

## Overview

This project uses **Claude Code Agent Teams** (released February 5, 2026) for coordinating multi-agent workflows. Agent Teams provides native support for:

- **Task dependencies** - Tasks automatically unblock when prerequisites complete
- **Direct teammate communication** - Agents coordinate without routing through lead
- **Shared task lists** - Self-claiming work distribution
- **File locking** - Prevents race conditions on concurrent edits

## Enabled Since

**Date**: February 13, 2026
**Configuration**: `.claude/settings.json` with `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS="1"`
**Migration**: Replaced Python hook-based orchestration (see `migration-plan.md`)

---

## 8 Specialized Teammates

### 1. **data-architect** - Design Lead
**When to spawn**: Schema design, SOMA layer decisions, data model architecture

**Spawn prompt**: `.claude/teams/prompts/data-architect.md`

**What they do**:
- Determine SOMA layer (activity, entity, metrics, nets)
- Define grain, primary key, and foreign keys
- Design dimension/fact relationships
- Choose materialization strategy

**What they create**:
- Implementation task(s) for dbt-engineer with complete design spec
- Metric definition tasks for metrics-analyst (if needed)
- Performance review tasks for performance-optimizer (if concerns exist)

---

### 2. **dbt-engineer** - Implementation Lead
**When to spawn**: Model implementation, SQL development, test creation

**Spawn prompt**: `.claude/teams/prompts/dbt-engineer.md`

**What they do**:
- Implement dbt models using Test-Driven Development (TDD)
- Write schema.yml with tests BEFORE SQL
- Run 6 mandatory self-verification gates
- Apply fixes from code review findings

**What they create**:
- Code review task for dbt-code-reviewer (ALWAYS after implementation)
- Impact analysis task for impact-analyzer (if modifying seeds/sources/dimensions)
- Clarification tasks for LEAD (if requirements unclear)

---

### 3. **dbt-code-reviewer** - Quality Specialist
**When to spawn**: Code review, PR review, quality validation

**Spawn prompt**: `.claude/teams/prompts/dbt-code-reviewer.md`

**What they do**:
- Review code using SOMA quality rubric (70/100 threshold)
- Provide auto-fix code for common issues
- Score readability, testing, documentation, SOMA compliance
- Maximum 3 review cycles before escalating

**What they create**:
- Fix task for dbt-engineer (if 🟡 changes requested or 🔴 needs rework)
- Re-review task for self with dependency on fix task
- Escalation task for LEAD (if fundamental issues, score < 60)
- Nothing (if 🟢 approved - workflow complete)

---

### 4. **impact-analyzer** - Safety Specialist
**When to spawn**: Before modifying seeds, sources, dimension attributes, or values in filters

**Spawn prompt**: `.claude/teams/prompts/impact-analyzer.md`

**What they do**:
- Execute 5-gate analysis process
- Trace downstream consumers and value-dependent filters
- Classify changes as SAFE / CAUTION / DANGEROUS
- **READ-ONLY** - never modifies code, only advises

**What they create**:
- Implementation task for dbt-engineer (if SAFE)
- Review task for LEAD (if CAUTION - requires user decision)
- Escalation task for LEAD with alternative approach (if DANGEROUS - blocked)

---

### 5. **metrics-analyst** - Metrics Lead
**When to spawn**: Metric definitions, validation, auditing

**Spawn prompt**: `.claude/teams/prompts/metrics-analyst.md`

**What they do**:
- Define metrics following SOMA methodology (atomic vs compound)
- Validate calculations against source systems
- Reconcile metric discrepancies
- Reference Levers Labs Metrics Library for standards

**What they create**:
- Implementation task for dbt-engineer (if new model needed)
- Validation task for self (after implementation)
- Fix task for dbt-engineer (if validation finds discrepancy)

---

### 6. **performance-optimizer** - Performance Lead
**When to spawn**: Slow queries, high costs, performance optimization

**Spawn prompt**: `.claude/teams/prompts/performance-optimizer.md`

**What they do**:
- Diagnose performance issues using Snowflake query history
- Analyze partitions scanned, bytes, spilling, TableScan %
- Recommend clustering, incremental strategies, warehouse sizing
- **A/B testing MANDATORY** - capture before/after metrics

**What they create**:
- Implementation task for dbt-engineer (if model changes needed)
- A/B test task for self (after optimization implemented)
- Alternative optimization task for self (if first attempt failed)
- Nothing (if recommendation-only, like warehouse sizing)

---

### 7. **retrospective-analyst** - Learning Specialist
**When to spawn**: After completed workflows, for capturing learnings

**Spawn prompt**: `.claude/teams/prompts/retrospective-analyst.md`

**What they do**:
- Analyze what went right/wrong in completed workflows
- Extract patterns and store in Letta via `memory_store`
- Enrich shallow reflections with detailed analysis
- Propose process improvements (only when 2+ occurrences detected)
- **MEMORY-ONLY** - never modifies code, writes only to Letta

**What they create**:
- Nothing (retrospective is terminal - no follow-up tasks)

---

### 8. **project-manager** - Team Lead (Use Sparingly)
**When to spawn**: Multi-feature projects (5+ models), coordinated releases

**Spawn prompt**: `.claude/teams/prompts/project-manager.md`

**When NOT to spawn**:
- Single feature implementation (lead coordinates directly)
- Bug fixes
- Simple 2-3 model workflows

**What they do**:
- Create Product Requirements Documents (PRDs)
- Break down into parent tasks (milestones) and subtasks
- Identify parallel vs sequential work
- Track progress and unblock issues
- Run acceptance verification

**What they create**:
- Milestone tasks (parent tracking)
- Subtasks assigned to appropriate agents
- Unblock tasks for LEAD (if blockers occur)
- User acceptance task for LEAD (final approval)

---

## Workflow Patterns

### Pattern 1: Simple Feature Implementation

```
User: "Add staging model for Salesforce opportunities"

Lead spawns:
→ data-architect: "Design stg_salesforce__opportunities"

data-architect completes, creates task:
→ dbt-engineer: "Implement stg_salesforce__opportunities" (depends on design)

dbt-engineer completes, creates task:
→ dbt-code-reviewer: "Review stg_salesforce__opportunities" (depends on implementation)

dbt-code-reviewer reviews:
  If 🟢 approved → Workflow COMPLETE
  If 🟡 changes → Creates fix task → dbt-engineer → Re-review → Loop until 🟢
  If 🔴 rework → Escalates to LEAD
```

**No manual handoffs needed** - tasks unblock automatically via dependencies.

---

### Pattern 2: Impact Analysis Before Change

```
User: "Change branch_type 'RETAIL' to 'RETAIL_STORE' in account_metadata"

Lead spawns:
→ impact-analyzer: "Analyze impact of changing 'RETAIL' → 'RETAIL_STORE'"

impact-analyzer executes 5-gate analysis:

Case A: SAFE (additive, no conflicts)
→ Creates implementation task for dbt-engineer
→ dbt-engineer → dbt-code-reviewer → COMPLETE

Case B: CAUTION (soft dependencies)
→ Creates review task for LEAD
→ LEAD approves → dbt-engineer proceeds

Case C: DANGEROUS (hard dependencies, data loss risk)
→ Creates escalation task for LEAD with alternative approach
→ Original change BLOCKED
→ LEAD decides: approve alternative, modify scope, or cancel
```

---

### Pattern 3: Metric Definition + Implementation + Validation

```
User: "Define Net Revenue Retention metric"

Lead spawns:
→ metrics-analyst: "Define NRR metric following SOMA methodology"

metrics-analyst defines metric, creates tasks:
→ dbt-engineer: "Implement met_nrr model" (depends on definition)
→ metrics-analyst (self): "Validate NRR calculation" (depends on implementation)

dbt-engineer completes, creates task:
→ dbt-code-reviewer: "Review met_nrr" (depends on implementation)

metrics-analyst validates:
  If matches → Workflow COMPLETE
  If discrepancy → Creates fix task → dbt-engineer → Re-validate → Loop until matches
```

---

### Pattern 4: Performance Optimization

```
User: "fct_orders is too slow"

Lead spawns:
→ performance-optimizer: "Diagnose and optimize fct_orders"

performance-optimizer analyzes, creates tasks:
→ dbt-engineer: "Add clustering to fct_orders" (depends on analysis)
→ performance-optimizer (self): "A/B test fct_orders performance" (depends on implementation)

dbt-engineer completes optimization
→ dbt-code-reviewer: "Review clustering config" (auto-created by engineer)

performance-optimizer A/B tests:
  If meets target (≥50% faster) → Documents baseline → COMPLETE
  If doesn't meet target → Creates alternative optimization task → Loop
```

---

## Task Creation Guidelines

### For Teammates

**See individual spawn prompts** (`.claude/teams/prompts/*.md`) for detailed task creation rules.

**General principles**:
1. **Mark your task COMPLETE** when done (with structured completion notes)
2. **Create follow-up tasks** based on your outcome (per spawn prompt scenarios)
3. **Set dependencies** correctly - dependent tasks unblock automatically
4. **Assign to correct teammate** - use role names (dbt-engineer, dbt-code-reviewer, etc.)
5. **Include context** - next agent needs full information to proceed

**Example task creation** (from dbt-engineer spawn prompt):
```
Title: "Code Review: fct_orders"
Assigned to: dbt-code-reviewer
Depends on: [implementation task ID]
Priority: High

Description:
Please review the implementation of fct_orders.

**Context**:
- SOMA Layer: activity
- Grain: One row per order_id
- Primary Key: order_id
- Upstream dependencies: dim_customers, dim_products

**Files to Review**:
- models/activities/fct_orders.sql
- models/activities/schema.yml

**Self-Verification Status**: All 6 gates passed
```

---

### For Lead Agent

**When to spawn teammates**:
- User request matches trigger words (see CLAUDE.md)
- Multi-step workflow needs coordination
- Specialized expertise required

**How to spawn**:
```
Lead: "I need to spawn data-architect teammate to design the customer LTV model.

Context:
- Business need: Track customer lifetime value
- Grain: One row per customer
- Upstream: fct_orders, dim_customers
- Metric: Sum of all order totals per customer

Please design the SOMA-compliant model."
```

**Teammate reads spawn prompt** (`.claude/teams/prompts/data-architect.md`) and follows task creation rules.

---

## Migration from Hook-Based System

**Migrated February 13, 2026** from Python hook orchestration to Agent Teams.

### What Changed

| Component | Old (Hooks) | New (Agent Teams) |
|-----------|-------------|-------------------|
| Routing | `pre-tool-use.py` trigger word matching | Lead assigns naturally |
| Workflow | `subagent-stop.py` HANDOFF_DIRECTIVE blocks | Task dependencies |
| Coordination | Stdout markdown injection | Shared task list |
| State | `.claude/workflow/queue.json` | Native Agent Teams state |

### What Stayed the Same

| Component | Status | Purpose |
|-----------|--------|---------|
| `session-start.py` | **KEPT** | Memory injection (patterns, reflections, episodes) |
| `post-tool-use.py` | **KEPT** | Build tracking (dbt success episodes) |
| `session-stop.py` | **KEPT** | Session archival and retrospective triggers |

**Memory system** - all memory is stored in Letta (pgvector-backed, semantically searchable).

### Rollback

If Agent Teams proves unstable, rollback in <5 minutes:

```bash
# 1. Disable Agent Teams
# Edit .claude/settings.json: Remove or set CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS="0"

# 2. Restore hooks
cp .claude/hooks/archive/hook-based-orchestration/*.py .claude/hooks/

# 3. Revert config
git checkout HEAD -- .claude/settings.json CLAUDE.md
```

See `.claude/teams/migration-plan.md` for full details.

---

## Documentation

- **Spawn Prompts**: `.claude/teams/prompts/*.md` (8 files, one per teammate)
- **Migration Plan**: `.claude/teams/migration-plan.md`
- **Test Scenarios**: `.claude/teams/test-scenarios.md`
- **Agent Definitions**: `.claude/agents/*.md` (full process details)

---

## Testing

**Verification workflows** defined in `test-scenarios.md`:

1. Simple Feature (data-architect → dbt-engineer → dbt-code-reviewer)
2. Review Feedback Loop (engineer ↔ reviewer until 🟢)
3. Impact Analysis DANGEROUS (analyzer → LEAD escalation, blocks change)
4. Metrics Definition (analyst → engineer → analyst validation)
5. Performance Optimization (optimizer → engineer → optimizer A/B test)

**Success criteria**: All workflows complete with task dependencies working correctly, no manual intervention needed.

---

## Tips for Using Agent Teams

1. **Let teammates self-coordinate** - they create follow-up tasks per spawn prompts
2. **Trust task dependencies** - don't manually invoke next agent
3. **Check spawn prompts** when spawning - they define task creation rules
4. **Use structured completion notes** - next agent needs context
5. **Escalate to LEAD when stuck** - don't create circular task dependencies
6. **Reference memory** - patterns, reflections, baselines inform decisions
7. **Use project-manager sparingly** - most workflows don't need it (lead coordinates directly)

---

## Support

- **Questions about Agent Teams**: See [Official Docs](https://code.claude.com/docs/en/agent-teams)
- **Issues with migration**: Check `migration-plan.md` for rollback instructions
- **Spawn prompt questions**: Read teammate's spawn prompt in `.claude/teams/prompts/`
- **Process improvements**: retrospective-analyst can propose changes to workflows
