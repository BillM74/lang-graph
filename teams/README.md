# Agent Teams Framework

Formalized coordination structure for complex multi-agent workflows.

## Overview

**Agent Teams** are coordinated groups of specialized agents that work together on complex tasks with:
- **Clear role definitions** - Each agent has specific expertise and responsibilities
- **Formal handoff protocols** - Structured communication between team members
- **Shared workspaces** - Team-level context and artifact storage
- **Phased workflows** - Sequential or parallel execution with validation gates
- **Success criteria** - Team-level goals that must be met

## Available Teams

### 1. Feature Development Team

**Purpose:** End-to-end feature implementation from design through deployment

**Coordinator:** project-manager

**Members:**
- data-architect (Phase 1: Design)
- impact-analyzer (Phase 1: Safety, conditional)
- dbt-engineer (Phase 2: Implementation)
- dbt-code-reviewer (Phase 3: Quality)
- performance-optimizer (Phase 3: Performance, conditional)

**When to use:**
- Implementing new analytics features
- Adding new models or data structures
- Complex multi-model implementations

**Typical workflow:**
```
Design → Impact Analysis → Implementation → Code Review → Validation → Commit
```

[Full specification →](feature-development.yml)

---

### 2. Metrics Team

**Purpose:** Define, implement, and validate SOMA-compliant metrics

**Coordinator:** metrics-analyst

**Members:**
- metrics-analyst (Phase 1: Definition, Phase 4: Validation)
- data-architect (Phase 2: Design, conditional)
- dbt-engineer (Phase 3: Implementation)

**When to use:**
- Defining new metrics (atomic or compound)
- Implementing metric calculations
- Validating and reconciling metrics

**Typical workflow:**
```
Define Metric → Design Data Model → Implement → Validate & Reconcile
```

[Full specification →](metrics-team.yml)

---

### 3. Performance Optimization Team

**Purpose:** Diagnose and fix Snowflake query performance and cost issues

**Coordinator:** performance-optimizer

**Members:**
- performance-optimizer (Phase 1: Diagnosis, Phase 3: Validation)
- dbt-engineer (Phase 2: Implementation)
- dbt-code-reviewer (Phase 3: Review)

**When to use:**
- Slow queries or dbt builds
- High Snowflake costs
- Query optimization needs

**Typical workflow:**
```
Diagnose Issue → Implement Optimization → A/B Test → Code Review → Document
```

[Full specification →](performance-team.yml)

---

### 4. Learning & Improvement Team

**Purpose:** Continuous improvement through retrospective analysis

**Coordinator:** retrospective-analyst

**Members:**
- retrospective-analyst (single-agent team)

**When to use:**
- After complex workflows complete
- When same issues recur multiple times
- Periodic learning reviews

**Typical workflow:**
```
Analyze Workflow → Extract Patterns → Propose Improvements
```

[Full specification →](learning-team.yml)

---

## How Agent Teams Work

### 1. Team Invocation

Teams are invoked by:

**Explicit invocation:**
```
User: "Use the feature-development team to build customer LTV tracking"
```

**Automatic routing (via project-manager):**
```
User: "Implement subscription churn tracking"
→ project-manager recognizes feature implementation
→ Invokes feature-development team
```

**Team-specific triggers:**
- "define a metric" → metrics-team
- "this query is slow" → performance-team
- "run a retrospective" → learning-team

### 2. Phased Execution

Teams execute in phases with validation gates:

```
Phase 1: Design & Planning
  ↓ (Gates must pass)
Phase 2: Implementation
  ↓ (Gates must pass)
Phase 3: Validation & Quality
  ↓ (Gates must pass)
Phase 4: Completion & Documentation
```

**Within phases:**
- Sequential execution (one agent after another)
- Parallel execution (multiple agents simultaneously)
- Conditional execution (only if specific conditions met)

### 3. Handoff Protocol

When one agent completes its work, it hands off to the next agent:

```markdown
## HANDOFF TO [NEXT_AGENT]

**Context:** What was completed in this phase
**Artifacts:**
  - Files created/modified
  - Key decisions made
**Next Steps:** What needs to happen next
**Success Criteria:** How to verify completion
**Status:** REQUIRED|OPTIONAL|COMPLETE
```

**Status meanings:**
- **REQUIRED** - Next agent must be invoked
- **OPTIONAL** - Next agent invocation is conditional/user choice
- **COMPLETE** - Workflow finished, no next agent

### 4. Shared Workspaces

Each team has a shared workspace for collaboration:

```
.claude/teams/
├── feature-dev/
│   ├── current-feature.md       # Active feature specification
│   ├── decisions.md             # Architecture decisions
│   ├── checklist.md             # Completion criteria
│   └── artifacts/               # Team outputs
├── metrics-team/
│   ├── metric-definitions/      # Metric specs being defined
│   ├── validation-results/      # Reconciliation outcomes
│   └── reconciliation-notes/    # Investigation findings
└── performance-team/
    ├── benchmarks/              # Before/after comparisons
    ├── optimization-plans/      # Proposed optimizations
    └── ab-test-results/         # Performance measurements
```

### 5. Validation Gates

Gates enforce quality at each phase:

| Gate Type | Description | Example |
|-----------|-------------|---------|
| **Technical** | Code must work | dbt compile/run/test pass |
| **Quality** | Meets standards | Code review approved |
| **Business** | Meets requirements | Metric matches definition |
| **Performance** | Meets efficiency targets | Query < 5min, cost < $X |
| **Safety** | No breaking changes | Impact analysis confirms SAFE |

**If a gate fails:**
- Fix the issue
- Re-run the gate
- Proceed only after passing

**Iterative refinement loop:**
```
Gate fails → Return to previous phase → Fix issue → Re-run gate → Continue
```

---

## Team Configuration (YAML)

Each team is defined in a YAML file with:

### Required Fields

```yaml
name: team-name
description: Team purpose
coordinator: agent-name  # Which agent orchestrates

members:
  - role: design
    agent: data-architect
    phase: 1
    required: true|false|conditional
    description: What this role does

shared_workspace: .claude/teams/team-name/

success_criteria:
  - Criterion 1
  - Criterion 2

workflow:
  phase_1_name:
    sequence:
      - step: 1
        agent: agent-name
        task: What to do
        outputs: [list of outputs]
        gates: [list of gates]
```

### Optional Fields

```yaml
handoff_protocol:
  format: |
    Handoff template

coordination_rules:
  - Rule 1
  - Rule 2

examples:
  - name: Example scenario
    flow: |
      Step-by-step flow
```

---

## Creating Custom Teams

To add a new team:

1. **Identify the workflow type**
   - What problem does this team solve?
   - Which agents are needed?
   - What's the typical workflow?

2. **Create team YAML**
   ```bash
   touch .claude/teams/my-team.yml
   ```

3. **Define team structure**
   ```yaml
   name: my-team
   description: Purpose of team
   coordinator: coordinating-agent
   members:
     - role: role1
       agent: agent1
       phase: 1
       required: true
       description: What they do
   ```

4. **Define workflow phases**
   ```yaml
   workflow:
     phase_1_name:
       sequence:
         - step: 1
           agent: agent1
           task: Do something
           outputs: [artifact1]
           gates: [gate1]
   ```

5. **Document success criteria**
   ```yaml
   success_criteria:
     - All tests pass
     - Code review approved
     - Performance acceptable
   ```

6. **Add examples**
   ```yaml
   examples:
     - name: Example 1
       flow: |
         Detailed flow description
   ```

---

## Team Coordination Patterns

### Pattern 1: Sequential Execution

Agents execute one after another:

```yaml
workflow:
  phase_1:
    sequence:
      - step: 1
        agent: agent-a
      - step: 2
        agent: agent-b  # Runs after agent-a
      - step: 3
        agent: agent-c  # Runs after agent-b
```

**Use when:** Each step depends on the previous step's output

### Pattern 2: Parallel Execution

Multiple agents work simultaneously:

```yaml
workflow:
  phase_2:
    parallel: true
    tasks:
      - agent: agent-a  # Run in parallel
      - agent: agent-b  # Run in parallel
```

**Use when:** Tasks are independent and don't depend on each other

### Pattern 3: Conditional Execution

Agent invoked only if conditions met:

```yaml
workflow:
  phase_1:
    sequence:
      - step: 2
        agent: impact-analyzer
        condition: modifying_existing_structures
```

**Use when:** Some steps are only needed in specific scenarios

### Pattern 4: Iterative Refinement

Loop back if validation fails:

```yaml
workflow:
  phase_3_validation:
    sequence:
      - step: validate
        agent: metrics-analyst
        gates:
          - Calculation matches definition
        on_failure: return_to_phase_2  # Loop back
```

**Use when:** Quality gates must pass, may need multiple attempts

---

## Comparison: Teams vs Individual Agents

| Aspect | Individual Agent | Agent Team |
|--------|------------------|------------|
| **Invocation** | Single-agent task | Multi-agent workflow |
| **Coordination** | None (standalone) | Formal handoffs |
| **Context** | Agent-specific | Team-shared workspace |
| **Success Criteria** | Agent-level | Team-level |
| **Complexity** | Simple tasks | Complex workflows |
| **Duration** | Minutes | Hours or days |

**Use individual agents for:**
- Quick implementations
- Single-step tasks
- Isolated reviews

**Use agent teams for:**
- Multi-phase projects
- Complex features requiring multiple skills
- Workflows needing formal coordination

---

## Example Team Workflows

### Example 1: Simple Feature (Feature Development Team)

```
User: "Add a staging model for Salesforce contacts"

1. project-manager: Invokes feature-development team
2. data-architect: Designs stg_salesforce__contacts
3. dbt-engineer: Implements model + tests
4. dbt-code-reviewer: Reviews (🟢 approved)
5. project-manager: Commits changes
```

**Team value:** Ensured design → implementation → review flow

---

### Example 2: Complex Feature with Safety Check

```
User: "Change branch_type values in account_metadata seed"

1. project-manager: Invokes feature-development team
2. data-architect: Reviews change request
3. impact-analyzer: Analyzes downstream impact → DANGEROUS (hardcoded in 12 WHERE clauses)
4. impact-analyzer: Recommends alternative fix
5. dbt-engineer: Implements correct fix (add new values, don't change existing)
6. dbt-code-reviewer: Reviews (🟢 approved)
7. project-manager: Commits
```

**Team value:** Safety gate prevented breaking 12 downstream models

---

### Example 3: Metric Definition (Metrics Team)

```
User: "Define Net Revenue Retention (NRR) metric"

1. metrics-analyst: Defines NRR as compound metric
2. metrics-analyst: Identifies components (starting MRR, expansion, contraction, churn)
3. dbt-engineer: Implements in net_retention_metrics
4. metrics-analyst: Validates → 102% (expected) ✓
5. metrics-analyst: Reconciles with finance report → 3% variance (acceptable)
6. Complete: NRR metric ready
```

**Team value:** Workflow ensures definition → implementation → validation

---

### Example 4: Performance Optimization (Performance Team)

```
User: "fct_orders query takes 5 minutes"

1. performance-optimizer: Diagnoses → Full table scan, no clustering
2. performance-optimizer: Recommends → Cluster on (order_date, customer_segment)
3. dbt-engineer: Adds clustering config
4. performance-optimizer: A/B test → 5min → 1min (5x faster) ✓
5. dbt-code-reviewer: Reviews changes (🟢 approved)
6. performance-optimizer: Documents in Letta baselines
7. Complete: Query optimized
```

**Team value:** Systematic optimization with validation and documentation

---

### Example 5: Retrospective (Learning Team)

```
Trigger: Feature-development workflow completed

1. retrospective-analyst: Analyzes session artifacts
2. retrospective-analyst: Finds 3 occurrences of missing impact analysis
3. retrospective-analyst: Extracts pattern: "Seed changes without impact analysis → breaking changes"
4. retrospective-analyst: Proposes improvement: "Mandatory impact-analyzer gate for all seed modifications"
5. retrospective-analyst: Stores proposal in Letta with tags ["proposal", "status:proposed"]
6. User reviews and approves
7. Complete: Process improved
```

**Team value:** Continuous learning prevents recurring issues

---

## Best Practices

### 1. Clear Role Assignment

Each agent should have a clear, non-overlapping role:
- ✅ "data-architect designs, dbt-engineer implements"
- ❌ "Both agents can do design or implementation"

### 2. Explicit Gates

Define what must pass before proceeding:
- ✅ "dbt compile succeeds, dbt test passes, review approved"
- ❌ "Code looks good"

### 3. Shared Context

Use team workspaces to maintain context:
- ✅ Store decisions in .claude/teams/team-name/decisions.md
- ❌ Rely on agent memory alone

### 4. Handoff Documentation

Document what's complete and what's next:
- ✅ Use formal handoff protocol template
- ❌ Assume next agent knows context

### 5. Success Criteria

Define clear, measurable team-level goals:
- ✅ "Query runtime < 5min, all tests pass, review approved"
- ❌ "Make it better"

---

## Troubleshooting Teams

### Issue: Team coordination is unclear

**Solution:** Review team YAML, ensure phases and handoffs are explicit

### Issue: Agent skipped or invoked wrong

**Solution:** Check coordination_rules, verify conditions are met

### Issue: Gates constantly failing

**Solution:** Gates may be too strict, review success_criteria

### Issue: Team workflow too slow

**Solution:** Identify opportunities for parallel execution

### Issue: Handoffs missing context

**Solution:** Enhance handoff_protocol template with more detail

---

## Future Enhancements

Potential improvements to agent teams:

1. **Team Templates** - Pre-built team configs for common workflows
2. **Team Metrics** - Success rate, duration, efficiency tracking
3. **Dynamic Team Assembly** - Auto-select agents based on task
4. **Team Replay** - Re-run team workflow on similar tasks
5. **Cross-Team Patterns** - Extract patterns across different teams

---

## Related Documentation

- [Agents README](../agents/README.md) - Individual agent documentation
- [Skills README](../skills/README.md) - Skills that agents use
- [Letta Memory](../../docs/letta_memory_integration_guide.md) - Persistent memory system
- [CLAUDE.md](../../CLAUDE.md) - Project-level agent delegation rules

---

**Note:** Agent teams are an advanced pattern for complex workflows. For simple tasks, individual agent invocation is sufficient and faster.
