# Custom Subagents

This directory contains custom subagents for the analytics project. Subagents are specialized AI assistants that Claude automatically invokes when their expertise is needed.

## Available Subagents

### 🏗️ Data Architect (`data-architect`)

**Purpose**: Expert data architect applying SOMA methodology for dbt, Snowflake, and dimensional modeling.

**When invoked**: Architectural guidance including:
- Data warehouse schema design
- dbt project structure (SOMA-compliant)
- Data modeling decisions (activities, entities, metrics)
- SOMA implementation and compliance
- Semantic layer and metrics architecture
- Best practices and standards

**Expertise areas**:
- SOMA (Standard Operating Metrics & Analytics)
- dbt project architecture and best practices
- Snowflake optimization and cost management
- Dimensional modeling (Kimball methodology)
- Metrics-first design
- Activity schema patterns

**Tools**: Read, Write, Edit, Bash, Glob, Grep, Task, WebSearch, WebFetch
**Model**: Sonnet

---

### 🔍 dbt Code Reviewer (`dbt-code-reviewer`)

**Purpose**: Expert code reviewer for dbt models, testing, and documentation quality.

**When invoked**: Code reviews including:
- Pull request reviews
- dbt model quality checks
- Testing coverage validation
- Documentation completeness
- SOMA compliance verification
- Best practices enforcement

**Review focus**:
- Model structure and organization
- SQL code quality and readability
- Testing coverage (unique, not_null, relationships)
- Documentation standards
- Naming conventions
- Performance patterns

**Tools**: Read, Glob, Grep, Bash
**Model**: Haiku (fast, cost-effective)

---

### 📊 Metrics Analyst (`metrics-analyst`)

**Purpose**: Expert in defining, validating, and maintaining SOMA-compliant metrics.

**When invoked**: Metrics work including:
- Defining new metrics (atomic and compound)
- Auditing existing metric definitions
- Troubleshooting metric discrepancies
- Validating metric calculations
- Ensuring SOMA compliance
- Metric governance and standards

**Expertise areas**:
- SOMA metric definitions
- Atomic vs compound metrics
- Metric categorization and ownership
- Business logic validation
- dbt Semantic Layer implementation
- Levers Labs metrics library

**Tools**: Read, Write, Edit, Grep, Bash, WebSearch
**Model**: Sonnet

---

### ⚡ Performance Optimizer (`performance-optimizer`)

**Purpose**: Expert in Snowflake and dbt performance optimization and cost reduction.

**When invoked**: Performance issues including:
- Slow query troubleshooting
- Cost optimization strategies
- Incremental model tuning
- Warehouse sizing and management
- Clustering strategies
- dbt build optimization

**Optimization focus**:
- Query execution plans
- Materialization strategies
- Warehouse right-sizing
- Cost monitoring and reduction
- Clustering and partitioning
- Query pattern improvements

**Tools**: Read, Bash, Grep, WebSearch
**Model**: Sonnet

---

### 🛡️ Impact Analyzer (`impact-analyzer`)

**Purpose**: Analyzes downstream impact of proposed data changes before implementation.

**When invoked**: Pre-change analysis including:
- Modifying seed file values (e.g., `account_metadata.csv`)
- Changing source definitions or mappings
- Altering dimension attribute values (region, department, branch_type)
- Any value used in downstream WHERE, CASE, or JOIN conditions

**Analysis process** (5-gate):
1. Change classification (additive vs mutative)
2. Downstream consumer trace (full dependency tree)
3. Value-dependent filter detection (hardcoded WHERE/CASE/JOIN)
4. Dimension source collision check (UNION ALL CTEs)
5. Impact assessment report (SAFE / CAUTION / DANGEROUS)

**Key principle**: Read-only — advises but does NOT modify files. Fixes go through `dbt-engineer`.

**Tools**: Read, Bash, Glob, Grep
**Model**: Sonnet

---

### 🔨 dbt Engineer (`dbt-engineer`)

**Purpose**: Expert dbt implementation engineer who builds models, tests, and documentation.

**When invoked**: Implementation work including:
- Building new dbt models
- Creating staging/intermediate/mart layers
- Writing SQL transformations
- Implementing incremental strategies
- Adding tests and documentation
- Building SOMA-compliant structures

**Implementation focus**:
- Writing production-quality SQL
- Creating schema.yml with tests
- Following naming conventions
- Implementing activities, entities, nets
- CTE patterns and best practices
- Comprehensive testing coverage

**Tools**: Read, Write, Edit, Bash, Glob, Grep
**Model**: Sonnet

---

### 🔄 Retrospective Analyst (`retrospective-analyst`)

**Purpose**: Examines completed workflows to identify what went right/wrong, writes lessons learned to memory, and proposes process improvements.

**When invoked**: Post-workflow analysis including:
- After complex multi-agent workflows complete
- On demand ("what did we learn?", "run a retrospective")
- When session-stop hook suggests a retrospective

**Analysis process** (4-phase):
1. Gather session artifacts (episodes, reflections, routing decisions)
2. Analyze successes and failures (test cycles, review iterations, discoveries)
3. Record enriched reflections and extract new patterns
4. Propose process improvements (only when 2+ occurrences of same issue)

**Key principle**: Writes only to Letta memory — proposes process changes but does not modify agent configs or model code directly.

**Tools**: Read, Write, Edit, Bash, Glob, Grep
**Model**: Sonnet

---

### 📋 Project Manager (`project-manager`)

**Purpose**: Expert project manager orchestrating PRD creation, task breakdown, and coordinated implementation.

**When invoked**: Project planning including:
- Creating Product Requirements Documents (PRDs)
- Breaking down requirements into tasks
- Coordinating multi-agent workflows
- Managing task execution and progress
- Ensuring quality gates and completeness

**Orchestration focus**:
- PRD generation with clarifying questions
- Task breakdown (parent tasks → sub-tasks)
- Agent delegation and coordination
- Progress tracking and commits
- Quality assurance workflow

**Tools**: Read, Write, Edit, Glob, Grep, Task
**Model**: Sonnet

## How Subagents Work

1. **Automatic Delegation**: Claude automatically invokes the appropriate subagent based on the task type
2. **Separate Context**: Each subagent operates with its own context window for focused work
3. **MCP Access**: Subagents have access to configured MCP servers (Snowflake, dbt, GitLab, Jira)
4. **Tool Access**: Only tools specified in the YAML frontmatter are available to each subagent
5. **Specialized Expertise**: Each agent brings domain-specific knowledge to the task

## Agent Collaboration Patterns

### Standard Development Workflow

The subagents work together to cover the full analytics lifecycle:

```
data-architect       → Designs the architecture (SOMA-compliant structure)
    ↓
dbt-engineer        → Implements the models, tests, and documentation
    ↓
dbt-code-reviewer   → Reviews implementation for quality and standards
    ↓
metrics-analyst     → Validates metrics definitions and calculations
    ↓
performance-optimizer → Optimizes queries and reduces costs
```

### Orchestrated Project Workflow (with project-manager)

For complex features requiring planning and coordination:

```
project-manager      → Creates PRD, breaks down into tasks, coordinates agents
    ↓
  ┌─────────────────┴─────────────────┐
  │   Phase 1: Requirements & Design  │
  └─────────────────┬─────────────────┘
                    ↓
metrics-analyst     → Define metrics in definitions/metrics/*.json
    ↓
data-architect      → Design data models and SOMA structure
    ↓
  ┌─────────────────┴─────────────────┐
  │   Phase 2: Implementation         │
  └─────────────────┬─────────────────┘
                    ↓
dbt-engineer        → Build models, tests, documentation
    ↓
dbt-code-reviewer   → Review code quality and conventions
    ↓
  ┌─────────────────┴─────────────────┐
  │   Phase 3: Validation             │
  └─────────────────┬─────────────────┘
                    ↓
metrics-analyst     → Validate calculations
    ↓
performance-optimizer → Optimize performance
    ↓
  ┌─────────────────┴─────────────────┐
  │   Phase 4: Completion             │
  └─────────────────┬─────────────────┘
                    ↓
project-manager     → Run tests, commit, mark tasks complete
```

**Example Workflows**:

**Workflow 1: Planned Feature (Orchestrated)**
1. User: "We need contribution margin tracking by branch"
2. **project-manager**: Creates PRD with clarifying questions
3. **project-manager**: Breaks down into task list
4. **project-manager**: Coordinates execution:
   - **metrics-analyst**: Define ContributionMargin metric
   - **data-architect**: Design aggregation model
   - **dbt-engineer**: Implement atomic metrics
   - **dbt-code-reviewer**: Review implementation
   - **metrics-analyst**: Validate calculations
   - **performance-optimizer**: Optimize aggregations
5. **project-manager**: Manages commits after each phase

**Workflow 2: Quick Implementation**
1. User: "Add a new staging model for customers"
2. **dbt-engineer** implements the model and tests
3. **dbt-code-reviewer** reviews for best practices
4. User commits changes

**Workflow 3: Code Review**
1. User creates a pull request
2. **dbt-code-reviewer** performs systematic review
3. **metrics-analyst** validates any metric changes
4. **performance-optimizer** flags performance concerns

**Workflow 4: Troubleshooting**
1. User reports "Query is slow"
2. **performance-optimizer** analyzes and recommends changes
3. **dbt-engineer** implements optimizations
4. **dbt-code-reviewer** verifies changes don't break conventions

## Creating New Subagents

To add more subagents to this project:

1. Create a new `.md` file in this directory
2. Add YAML frontmatter with required fields:
   ```markdown
   ---
   name: your-agent-name
   description: When this agent should be invoked
   tools: Tool1, Tool2, Tool3  # Optional, omit to inherit all
   model: sonnet  # Optional: sonnet, opus, haiku, or inherit
   ---

   System prompt and instructions...
   ```
3. Write detailed instructions for the agent's role and responsibilities
4. The agent will be automatically available in the next Claude session

## Additional Subagent Ideas

Consider creating these additional subagents for your analytics project:

- **Data Quality Engineer** - Designs comprehensive testing strategies, anomaly detection
- **Documentation Writer** - Creates and maintains clear project documentation
- **DevOps Engineer** - Manages CI/CD, deployment, and infrastructure as code
- **Business Analyst** - Translates business requirements into technical specifications
- **Data Governance Lead** - Ensures compliance, security, and access control
- **SQL Educator** - Teaches SQL best practices to team members

## Best Practices

### Writing Effective Subagent Prompts

1. **Clear Role Definition**: State exactly what the agent is responsible for
2. **Specific Instructions**: Provide step-by-step guidance for common tasks
3. **Concrete Examples**: Show what good output looks like
4. **Constraints**: Define boundaries and limitations
5. **Context**: Explain the project environment and standards

### Tool Selection

- **Minimal toolset**: Only grant tools necessary for the agent's purpose
- **Read-heavy agents**: Give Read, Glob, Grep for analysis-focused agents
- **Action agents**: Add Write, Edit, Bash for agents that modify code
- **Research agents**: Include WebSearch, WebFetch for agents that need external info

### Model Selection

- **Haiku**: Fast, cost-effective for simple, well-defined tasks
- **Sonnet**: Balanced performance for most architectural and coding tasks (default)
- **Opus**: Maximum capability for complex reasoning and design work
- **Inherit**: Use the same model as the main conversation

## Testing Your Subagent

After creating a subagent:

1. **Restart Claude** or start a new conversation
2. **Trigger invocation** by asking questions in the agent's domain
3. **Verify behavior** - Check that the agent is invoked and responds appropriately
4. **Refine prompts** - Update the system prompt based on observed behavior
5. **Iterate** - Continuously improve based on usage

## File Structure

```
.claude/
└── agents/
    ├── README.md                    # This file
    ├── project-manager.md           # PRD/task orchestrator (Orchestration)
    ├── data-architect.md            # SOMA-based data architecture expert (Advisory)
    ├── metrics-analyst.md           # Metrics definition and validation expert (Advisory)
    ├── dbt-engineer.md              # dbt implementation engineer (Builder)
    ├── dbt-code-reviewer.md         # dbt code quality reviewer (Quality)
    ├── performance-optimizer.md     # Snowflake and dbt performance expert (Optimization)
    ├── impact-analyzer.md           # Pre-change impact analysis (Safety)
    ├── retrospective-analyst.md     # Post-workflow learning (Learning)
    └── [your-agent].md              # Additional custom agents
```

## Agent Types

**Orchestration Agents** (Planning & Coordination):
- project-manager - Creates PRDs, breaks down tasks, coordinates agents

**Advisory Agents** (Design & Guidance):
- data-architect - Designs architecture
- metrics-analyst - Defines and validates metrics

**Implementation Agents** (Build):
- dbt-engineer - Writes code and implements features

**Safety Agents** (Impact & Risk):
- impact-analyzer - Analyzes downstream impact before data changes

**Learning Agents** (Retrospective & Improvement):
- retrospective-analyst - Examines workflows, extracts patterns, proposes improvements

**Quality Agents** (Review & Optimize):
- dbt-code-reviewer - Reviews code quality
- performance-optimizer - Optimizes performance

## References

- [Claude Code Subagents Documentation](https://code.claude.com/docs/en/sub-agents)
- [SOMA Framework (Levers Labs)](https://github.com/Levers-Labs/SOMA-B2B-SaaS)
- [Levers Labs Metrics Library](https://www.leverslabs.com/metrics-library)
- [dbt Best Practices](https://docs.getdbt.com/best-practices)
- [dbt Semantic Layer](https://docs.getdbt.com/docs/build/metrics)
- [Snowflake Documentation](https://docs.snowflake.com/)
- [Kimball Dimensional Modeling](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/)

## Agent Improvement & Feedback

To continuously improve agents, we use a structured feedback loop:

**Feedback Process**:
1. **Collect** - Use templates in `.claude/feedback/` after each significant interaction
2. **Analyze** - Weekly review of feedback, metrics, and outcomes
3. **Improve** - Update agent prompts, examples, and context
4. **Track** - Maintain version history and measure success metrics

**Quick Feedback**:
```markdown
## 2025-11-11 - dbt-engineer

**Task**: Implement customer churn metric

**Issue**: Missed adding clustering key

**Fix**: Add clustering checklist to implementation steps

**Priority**: Medium
```

**Detailed Feedback**:
- Use [TEMPLATE-feedback.md](../feedback/TEMPLATE-feedback.md) after major tasks
- Rate agent performance on accuracy, completeness, clarity, efficiency
- Identify root causes and suggested improvements

**Knowledge Accumulation**:
- [common-patterns.md](../learnings/common-patterns.md) - Patterns and anti-patterns
- [agent-specific/](../learnings/agent-specific/) - Agent-specific learnings
- [case-studies/](../learnings/case-studies/) - Detailed implementation stories

**Weekly Review Cycle**:
- Monday: Collect and review all feedback
- Tuesday: Prioritize improvements by impact
- Wednesday-Thursday: Update agent prompts
- Friday: Test changes and document in CHANGELOG

**Success Metrics**:
- First-time success rate
- Code review approval rate
- Test passing rate
- Time to task completion
- User satisfaction ratings

See [AGENT_FEEDBACK.md](../AGENT_FEEDBACK.md) for the complete feedback system documentation.

## Skills Integration

This project also uses **Skills** alongside Agents. Skills provide contextual guidance that Claude applies automatically or on demand.

### Skills vs Agents

| Feature | Skills | Agents |
|---------|--------|--------|
| **Invocation** | Auto OR explicit `/skill` | Auto delegation |
| **Context** | Current conversation | Separate context |
| **Purpose** | Knowledge, checklists | Multi-step tasks |

### How They Work Together

```
User: "Add contribution margin tracking"
         │
         ├── soma-patterns SKILL (injects SOMA guidance)
         │
         ├── metrics-analyst AGENT (defines the metric)
         │
         ├── dbt-engineer AGENT (implements the model)
         │
         └── dbt-testing SKILL (injects test standards)
```

### Available Skills

| Skill | Type | Purpose |
|-------|------|---------|
| `soma-patterns` | Auto | SOMA methodology when editing models |
| `pr-review` | Both | PR review checklist |
| `metric-definition` | Explicit | Metric creation workflow |
| `dbt-testing` | Auto | Testing standards for schema.yml |
| `snowflake-optimization` | Explicit | Performance tuning reference |

See [Skills README](../skills/README.md) for full documentation.

---

## Advanced Capabilities (2026 Update)

These bleeding-edge AI agent techniques were added to improve agent performance and learning.

### Memory System (Letta)

Agents share a persistent memory system backed by **Letta** (self-hosted, pgvector). All memories are semantically searchable via the `letta-memory` MCP server.

**Memory types:**
- **Archival memory** — semantically searchable passages (episodes, patterns, reflections, baselines, proposals)
- **Core memory** — structured blocks always in context (project_context, preferences, learned_patterns)

**Tag conventions for archival memory:**
| Tag | Content |
|-----|---------|
| `episode` | Build events, test results, significant actions |
| `pattern` | Reusable patterns (test failures, optimizations) |
| `reflection` | Post-task reflections |
| `baseline` | Performance baselines for models |
| `proposal` | Process improvement proposals |
| `routing` | Agent routing decisions |
| `pending-reflection` | Reflections that need enrichment |

**How agents use memory (automated by hooks):**

Memory operations are **automated by Claude Code hooks** in `.claude/hooks/`:

| Hook | Event | Automation |
|------|-------|------------|
| `session-start.py` | SessionStart | Searches Letta for recent episodes, patterns, pending reflections |
| `subagent-stop.py` | SubagentStop | Stores pending reflections in Letta, suggests next agent |
| `session-stop.py` | Stop | Archives session, stores retrospective suggestions in Letta |
| `post-tool-use.py` | PostToolUse | Stores successful dbt builds in Letta automatically |
| `pre-tool-use.py` | PreToolUse | Validates agent routing, logs decisions to Letta |

Agents can also directly use `memory_search` and `memory_store` for on-demand memory access.

### Self-Verification Gates (dbt-engineer)

Before marking any task complete, dbt-engineer runs 6 mandatory gates:

| Gate | Check | Must Pass |
|------|-------|-----------|
| 1 | `dbt compile` | No errors |
| 2 | `dbt run` | Model succeeds |
| 3 | `dbt test` | All tests pass |
| 4 | Documentation | Grain + PK documented |
| 5 | Downstream | No breaking changes |
| 6 | Functional | Semantic validation queries pass |

This prevents incomplete work from being marked done.

### Test-First Development (dbt-engineer)

dbt-engineer now follows TDD workflow:
1. Write `schema.yml` tests BEFORE implementing SQL
2. Define expected grain and primary key
3. Add relationship tests for foreign keys
4. THEN implement the SQL model
5. Iterate until all tests pass

### Parallel Agent Dispatch (project-manager)

project-manager can now run independent agents simultaneously:

```
Phase 1 (PARALLEL):
  ├── metrics-analyst: Define metrics
  └── data-architect: Design schema

Phase 2 (SEQUENTIAL - needs Phase 1):
  └── dbt-engineer: Implement models

Phase 3 (PARALLEL):
  ├── dbt-code-reviewer: Review code
  └── metrics-analyst: Validate calculations
```

**Parallelization rules:**
- ✅ Independent tasks with no shared dependencies
- ❌ Tasks where one needs output from another

### Auto-Fix Suggestions (dbt-code-reviewer)

Code reviewer now provides exact fix code, not just descriptions:

```
🟡 SUGGESTION [fct_orders.sql:45]

Missing FK test for customer_id.

**Auto-Fix - Add to schema.yml:**
- name: customer_id
  data_tests:
    - relationships:
        to: ref('dim_customers')
        field: customer_id
```

| Issue Type | Auto-Fix Template |
|------------|-------------------|
| Missing PK test | `data_tests: [unique, not_null]` |
| Missing FK test | `relationships: {to: ref('dim'), field: pk}` |
| Missing grain doc | `description: "Grain: one row per X"` |
| Unsafe division | `NULLIF(denominator, 0)` |

### A/B Comparison (performance-optimizer)

Performance optimizer now requires measured before/after comparison:

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Runtime | 120s | 30s | 4x faster |
| Bytes scanned | 50GB | 12GB | 75% reduction |
| Spilling | Yes | No | Eliminated |

Results are stored in Letta memory with tag `baseline` for tracking over time.

### Tree of Thought (data-architect)

For major architectural decisions, data-architect explicitly explores alternatives:

```
Decision: Incremental strategy for large fact table

Thought 1: Append strategy
  → Pros: Simple, fast
  → Cons: No updates supported
  → Score: 6/10

Thought 2: Merge strategy
  → Pros: Handles updates
  → Cons: Slower, needs unique key
  → Score: 8/10

Thought 3: Delete+insert by partition
  → Pros: Clean rebuilds per day
  → Cons: More complex logic
  → Score: 7/10

Recommendation: Merge - updates are common
Confidence: 4/5
```

### Self-Reflection Protocol (All Agents)

Every agent now records reflections after significant tasks:

```markdown
## Task Reflection - [Task Name]

**Date:** 2026-01-14
**Outcome:** Success/Partial/Failed

### What Worked
- [Effective approaches]

### Challenges
- [Issues encountered]

### Learning
- [What to do differently]

### Confidence Score: [1-5]
```

Reflections are stored in Letta memory with tag `reflection` by type.

---

## Related Documentation

- [Skills README](../skills/README.md) - Claude Code skills for this project
- [SOMA Implementation Guide](../SOMA_GUIDE.md) - Comprehensive SOMA methodology guide
- [Project Context](../PROJECT_CONTEXT.md) - Project-specific patterns and conventions
- [Agent Feedback System](../AGENT_FEEDBACK.md) - Continuous improvement process
- [Rules](../../rules/) - Workflow rules for PRD and task management
  - `create-prd.mdc` - PRD generation workflow
  - `generate-tasks.mdc` - Task breakdown process
  - `process-task-list.mdc` - Task execution protocol

---

**Note**: Subagents are project-scoped and will be available to all team members working on this codebase. Consider team standards and conventions when creating shared subagents.
