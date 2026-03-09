# Agent Teams Migration Plan

## Context

The current analytics project uses a custom Python hook-based orchestration system with 8 specialized agents (data-architect, dbt-engineer, dbt-code-reviewer, metrics-analyst, performance-optimizer, impact-analyzer, retrospective-analyst, project-manager). Orchestration is handled by 5 Python hooks that manage routing, workflow chains, memory injection, build tracking, and session archival.

On February 5, 2026, Claude Code released **Agent Teams** (with Opus 4.6) - a native feature providing built-in dependency management, direct teammate communication, shared task lists, and file locking. The February 10, 2026 repo review by Cali LaFollett & Marvin recommended migrating to Agent Teams to:
- Reduce orchestration complexity (eliminate 2 custom hooks)
- Improve parallelization (direct teammate communication vs routing through lead)
- Future-proof the system (native support from Anthropic)
- Preserve the valuable custom memory system

This migration will replace Python-based routing and handoff logic with Agent Teams' native features while keeping the memory hooks that provide unique value.

---

## Migration Approach

### What Changes

**Remove these hooks** (replaced by Agent Teams):
- `pre-tool-use.py` - Routing guard with trigger word matching → Lead naturally assigns tasks to correct teammates
- `subagent-stop.py` - Handoff directives (HANDOFF_DIRECTIVE markdown) → Task dependencies and teammate self-coordination

**Keep these hooks** (unique value, no Agent Teams equivalent):
- `session-start.py` - Memory injection (patterns, reflections, episodes, workflow queue)
- `post-tool-use.py` - Build tracking (dbt success episodes)
- `session-stop.py` - Session archival and retrospective triggers

**Migrate workflow patterns**:
- `dbt-engineer → dbt-code-reviewer → [loop if issues]` becomes task dependencies with teammates creating follow-up tasks
- `impact-analyzer → [dbt-engineer if SAFE] or [USER if DANGEROUS]` becomes conditional task creation
- Project-manager orchestration becomes native Agent Teams lead coordination

---

## Implementation Steps

### Step 1: Enable Agent Teams (Dual Mode Testing)

**File**: `.claude/settings.json`

Add experimental flag while keeping all hooks active for 1-2 weeks of parallel testing:

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  },
  "teammateMode": "auto",
  "hooks": {
    // All 5 hooks remain active during dual mode
    "SessionStart": [...],
    "SubagentStop": [...],
    "Stop": [...],
    "PreToolUse": [...],
    "PostToolUse": [...]
  }
}
```

**Verification**: Run test workflows with both Task tool (old) and Agent Teams (new), compare outcomes.

---

### Step 2: Create Teammate Spawn Prompts

**Directory**: `.claude/teams/prompts/`

Create spawn prompt templates for each agent role with task creation rules:

**Example**: `.claude/teams/prompts/dbt-code-reviewer.md`
```markdown
## dbt Code Reviewer Teammate

Review [model] implementation using SOMA code review rubric.

**If score >= 70 (🟢 APPROVED)**:
- Mark your review task COMPLETE
- Add note: "✅ APPROVED - Ready to merge"
- No new tasks needed

**If score < 70 (🟡 CHANGES REQUESTED)**:
- Mark your review task COMPLETE
- Create new task: "Fix: [specific issues]" assigned to dbt-engineer
  - Include auto-fix code snippets in task description
  - Set dependency: Must complete before re-review
- Create new task: "Re-review after fixes" assigned to self
  - Set dependency: Previous fix task

**If score < 50 (🔴 NEEDS REWORK)**:
- Mark your review task COMPLETE
- Create task: "ESCALATION: Major rework needed" assigned to LEAD
- Recommend: Return to design phase
```

Create prompts for all 8 agent roles with clear task creation rules for workflow continuation.

---

### Step 3: Update CLAUDE.md Delegation Rules

**File**: `CLAUDE.md`

**Update "Mandatory Agent Delegation" section**:

Replace Task tool instructions with Agent Teams patterns:

```markdown
### How to Delegate with Agent Teams

**For multi-step workflows**: Use Agent Teams by describing the workflow:

Example:
"Implement customer LTV tracking using feature-development team:
- data-architect: Design the model
- impact-analyzer: Check for breaking changes (if modifying existing structures)
- dbt-engineer: Implement models and tests
- dbt-code-reviewer: Review code quality"

**Team selection guide**:
- `feature-development` team for new models/features
- `metrics-team` for metric definitions
- `performance-team` for slow queries
- `learning-team` for retrospectives
```

**Update "Automatic Workflow Continuation" section**:

Replace HANDOFF_DIRECTIVE with task dependency explanation:

```markdown
### Workflow Continuation with Agent Teams

Agent Teams use **task dependencies** for automatic continuation:

1. Lead creates initial tasks with dependencies
2. Teammates complete tasks and mark DONE
3. Teammates create follow-up tasks if needed (per spawn prompt rules)
4. Dependent tasks unblock automatically

**Example workflow**:
Task 1: "Design model" (data-architect) → COMPLETE
  ↓ (dependency satisfied)
Task 2: "Implement model" (dbt-engineer) → STARTS AUTOMATICALLY
  ↓ (completes, creates follow-up)
Task 3: "Review implementation" (dbt-code-reviewer) → STARTS AUTOMATICALLY
  ↓ (finds issues 🟡, creates follow-up)
Task 4: "Fix review findings" (dbt-engineer) → STARTS AUTOMATICALLY
  ↓ (completes)
Task 5: "Re-review after fixes" (dbt-code-reviewer) → STARTS AUTOMATICALLY
  ↓ (approves 🟢)
Workflow COMPLETE

No manual handoffs needed - teammates coordinate via shared task list.
```

---

### Step 4: Progressive Hook Removal

After 1-2 weeks of successful dual mode testing:

**4a. Remove routing guard**:

Edit `.claude/settings.json` to remove `PreToolUse` hook:

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  },
  "hooks": {
    "SessionStart": [...],
    "SubagentStop": [...],  // Keep for now
    "PostToolUse": [...],
    "Stop": [...]
    // PreToolUse removed
  }
}
```

Test for 1 week: Verify lead assigns tasks to correct teammates without trigger word matching.

**4b. Remove handoff directives**:

Edit `.claude/settings.json` to remove `SubagentStop` hook:

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  },
  "hooks": {
    "SessionStart": [...],
    "PostToolUse": [...],
    "Stop": [...]
    // SubagentStop removed
  }
}
```

Test for 1 week: Verify task dependencies handle workflow chains without HANDOFF_DIRECTIVE blocks.

---

### Step 5: Archive Removed Hooks

Don't delete - preserve for rollback:

```bash
mkdir -p .claude/hooks/archive/hook-based-orchestration/
mv .claude/hooks/pre-tool-use.py .claude/hooks/archive/hook-based-orchestration/
mv .claude/hooks/subagent-stop.py .claude/hooks/archive/hook-based-orchestration/
```

Create archive README documenting what was replaced and rollback instructions:

`.claude/hooks/archive/hook-based-orchestration/README.md`:
- What each hook did
- What Agent Teams feature replaced it
- Rollback instructions (restore files + disable feature flag)
- Migration date and documentation reference

---

### Step 6: Create Documentation

**New files**:

1. `.claude/teams/README-AGENT-TEAMS.md` - How to use Agent Teams with this project's specialized roles
2. `.claude/teams/prompts/README.md` - Index of all teammate spawn prompts
3. `.claude/teams/migration-plan.md` - This plan (archive copy for reference)
4. `.claude/teams/test-scenarios.md` - 5 test workflows for verification

---

## Critical Files

| File | Purpose | Changes Needed |
|------|---------|----------------|
| `.claude/settings.json` | Enable Agent Teams, remove orchestration hooks | Add env flag, progressive hook removal |
| `CLAUDE.md` | User-facing delegation instructions | Update "Mandatory Agent Delegation" and "Automatic Workflow Continuation" sections |
| `.claude/hooks/pre-tool-use.py` | Routing guard (TO BE REMOVED) | Archive after testing |
| `.claude/hooks/subagent-stop.py` | Handoff directives (TO BE REMOVED) | Archive after testing |
| `.claude/hooks/session-start.py` | Memory injection (KEEP) | No changes |
| `.claude/hooks/post-tool-use.py` | Build tracking (KEEP) | No changes |
| `.claude/hooks/session-stop.py` | Session archival (KEEP) | No changes |
| `.claude/teams/prompts/*.md` | Teammate spawn prompts (NEW) | Create 8 files with task creation rules |

---

## Verification Plan

### Test Scenarios

Run these 5 workflows to verify Agent Teams migration:

**Test 1: Simple Feature Implementation**
- Task: Add staging model for Salesforce opportunities
- Team: feature-development
- Agents: data-architect → dbt-engineer → dbt-code-reviewer
- Success: All tasks complete in order, model builds, tests pass, no manual intervention

**Test 2: Review Feedback Loop**
- Task: Implementation with quality issues
- Team: feature-development
- Agents: dbt-engineer → dbt-code-reviewer (🟡 changes requested) → dbt-engineer (fixes) → dbt-code-reviewer (🟢 approved)
- Success: Reviewer creates fix task, engineer addresses issues, re-review happens automatically, loop terminates

**Test 3: Impact Analysis (DANGEROUS Classification)**
- Task: Change seed value referenced in downstream filters
- Team: feature-development
- Agents: impact-analyzer → LEAD (escalation)
- Success: Analyzer classifies as DANGEROUS, no implementation task created, lead escalates to user, alternative approach provided

**Test 4: Metrics Definition**
- Task: Define and validate Net Revenue Retention metric
- Team: metrics-team
- Agents: metrics-analyst → dbt-engineer → metrics-analyst (validation)
- Success: Metric defined with formula, implementation matches, validation confirms correctness

**Test 5: Performance Optimization**
- Task: Optimize slow fct_orders query
- Team: performance-team
- Agents: performance-optimizer → dbt-engineer → performance-optimizer (A/B test)
- Success: Diagnosis identifies root cause, optimization implemented, performance improvement measured, baseline documented

### Success Criteria

| Category | Check |
|----------|-------|
| **Functionality** | All 5 test workflows pass |
| **Memory** | session-start.py still injects context |
| **Memory** | post-tool-use.py still tracks builds |
| **Memory** | session-stop.py still triggers retrospectives |
| **Coordination** | Task dependencies work correctly |
| **Coordination** | Teammates create follow-up tasks appropriately |
| **Safety** | Impact analysis prevents breaking changes |
| **Quality** | Review feedback loops complete without manual intervention |
| **Documentation** | CLAUDE.md reflects new patterns |
| **Rollback** | Archived hooks can be restored |

**Minimum passing**: 9/10 checks (allow 1 minor issue for post-migration fix)

---

## Rollback Plan

If verification fails or Agent Teams proves unstable:

1. **Disable Agent Teams**:
   ```json
   {"env": {"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "0"}}
   ```

2. **Restore archived hooks**:
   ```bash
   cp .claude/hooks/archive/hook-based-orchestration/*.py .claude/hooks/
   ```

3. **Revert configuration files**:
   ```bash
   git checkout HEAD -- .claude/settings.json CLAUDE.md
   ```

4. **Document issues** in `.claude/teams/migration-issues.md` with what failed and why

**Recovery time**: < 5 minutes (all changes are configuration, no code impact)

---

## Implementation Timeline

- **Week 1**: Create spawn prompts, update CLAUDE.md, document test scenarios, git tag `v1-hook-based`
- **Week 2**: Enable Agent Teams (dual mode), run parallel tests, document findings
- **Week 3**: Remove pre-tool-use.py, test routing (1 week), remove subagent-stop.py, test workflows (1 week)
- **Week 4**: Run all verification tests, complete checklist, create migration retrospective

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Agent Teams has bugs (experimental) | Incremental migration with rollback plan |
| Task coordination fails | Keep subagent-stop.py until proven stable |
| Token costs increase significantly | Monitor usage during dual mode, set alerts |
| Teammates don't create follow-up tasks | Enhance spawn prompts with explicit task creation rules |
| Review loops infinite | Add max iteration limit (3) in reviewer spawn prompt |
| DANGEROUS changes bypass safety | Rigorous testing of impact-analyzer task creation (Test 3) |

---

## Key Benefits

1. **Reduced complexity**: Eliminate 2 custom hooks (400+ lines of Python)
2. **Better parallelization**: Teammates communicate directly, not through lead bottleneck
3. **Native support**: Agent Teams will receive ongoing improvements from Anthropic
4. **Preserved strengths**: Memory system (episodes, patterns, reflections) continues functioning
5. **Maintained safety**: Impact analysis and review loops work via task dependencies
6. **Incremental rollback**: Can restore hook-based system in < 5 minutes if needed
