---
name: agent-router
description: Routes tasks to appropriate specialized agents based on task type. Use when: receiving new implementation tasks, code review requests, performance issues, metric definitions, architecture design, or impact analysis. Determines if delegation to specialized agents is needed.
---

# Agent Router

Determines when to delegate work to specialized agents vs. handle directly.

## Routing Decision Tree

```
NEW TASK RECEIVED
    │
    ├─► "Review" in request?
    │   └─► YES → Delegate to dbt-code-reviewer
    │
    ├─► "Slow query" or "performance" or "optimize"?
    │   └─► YES → Delegate to performance-optimizer
    │
    ├─► "New metric" or "define metric" or "KPI"?
    │   └─► YES → Delegate to metrics-analyst
    │
    ├─► "Design" or "architecture" or "schema"?
    │   └─► YES → Delegate to data-architect
    │
    ├─► "Build model" or "implement" + multiple files?
    │   └─► YES → Delegate to dbt-engineer
    │
    ├─► "Fix" or "bug" or "debug" or "broken" or "error"?
    │   └─► YES → Delegate to dbt-engineer
    │
    ├─► "Impact" or "before changing" or "what depends on" or "safe to change" or "downstream impact"?
    │   └─► YES → Delegate to impact-analyzer
    │
    ├─► "Retrospective" or "what did we learn" or "lessons learned" or "what went wrong"?
    │   └─► YES → Delegate to retrospective-analyst
    │
    ├─► "Plan" or "PRD" or "project"?
    │   └─► YES → Delegate to project-manager
    │
    └─► Config-only change (< 20 lines, non-SQL)?
        └─► YES → Handle directly (no delegation)
```

## Delegation Commands

When routing to an agent, use the Task tool:

```
Task(
    subagent_type="<agent-name>",
    prompt="<detailed task description with context>",
    description="<3-5 word summary>"
)
```

## Agent Capabilities Quick Reference

| Agent | Use For | Model |
|-------|---------|-------|
| `dbt-code-reviewer` | PR reviews, code quality checks | Haiku (fast/cheap) |
| `performance-optimizer` | Slow queries, cost reduction | Sonnet |
| `metrics-analyst` | Metric definitions, validation | Sonnet |
| `data-architect` | Schema design, SOMA compliance | Sonnet |
| `dbt-engineer` | Model implementation | Sonnet |
| `impact-analyzer` | Pre-change impact analysis | Sonnet |
| `retrospective-analyst` | Post-workflow learning and proposals | Sonnet |
| `project-manager` | Multi-phase projects, PRDs | Sonnet |

## When NOT to Delegate

Handle directly when:
- Config-only edits (< 20 lines, non-SQL files like dbt_project.yml, profiles.yml)
- Applying feedback from a completed agent review
- Running dbt commands only (build, test, compile)
- Answering questions (no implementation)
- User explicitly says "don't use agents" or "do it yourself"

**Note:** Bugfixes always use agents (dbt-engineer) regardless of size.

## Parallel Delegation

For complex tasks, delegate to multiple agents in parallel:

```
# Example: New feature implementation
Task(subagent_type="data-architect", prompt="Design schema for...", ...)
Task(subagent_type="metrics-analyst", prompt="Define metrics for...", ...)
# Wait for both, then:
Task(subagent_type="dbt-engineer", prompt="Implement designs from...", ...)
```

## Enforcing Delegation

To ensure agents are used, the main agent should:

1. **Check this skill first** when receiving a new task
2. **Match against routing rules** before starting work
3. **Delegate if rules match** - don't just "do it yourself"
4. **Document why** if choosing not to delegate

### Self-Check Before Working

Before starting any task, ask:
- "Does this match a delegation rule?"
- "Would a specialized agent do this better?"
- "Is this a multi-step task that needs orchestration?"

If YES to any → Delegate to appropriate agent.

## Workflow Continuation Protocol

When a **HANDOFF DIRECTIVE** appears after agent completion, you MUST follow it:

### REQUIRED Handoffs

Invoke the next agent immediately without asking:
1. Read the directive's "Next Agent" and "Reason"
2. Include context from the completed agent's output
3. Execute the Task() call

### OPTIONAL Handoffs

Ask user if they want to continue:
1. Show what the next agent would do
2. Wait for user confirmation

### Code Review → Fix Cycle

This is the most common workflow:

```
dbt-engineer completes
       ↓
dbt-code-reviewer runs
       ↓
   ┌───┴───┐
   ↓       ↓
🟢 Approved    🟡/🔴 Changes
   ↓            ↓
COMPLETE    dbt-engineer (fixes)
               ↓
         dbt-code-reviewer (re-review)
```

### Context Passing

When invoking the next agent after a review, include:
1. Summary of previous agent's findings
2. Specific files/models to act on
3. Blocking issues that must be addressed

Example handoff to dbt-engineer after review:
```
Task(
    subagent_type="dbt-engineer",
    prompt="Address code review findings from dbt-code-reviewer:

    **Blocking Issues:**
    - [File:Line] Issue description

    **Suggestions:**
    - [List from review]

    After fixing, verification gates will be re-run.",
    description="Fix review findings"
)
```

### Override

User can say "skip handoff" or "don't continue workflow" to bypass automatic continuation.
