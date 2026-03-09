# LEARNED.md — agent-router

> Machine-generated from pattern data. Do not edit manually.
> Last updated: 2026-03-02

## Graduated

### dbt_engineer_primary_workhorse ✓
- **Source**: routing-decisions.json (55 entries analyzed)
- **Graduated**: 2026-03-02
- **Description**: dbt-engineer is the most frequently routed agent (~50% of all routing decisions), handling implementation, bugfixes, model creation, and applying review fixes
- **Routing Rule**: Route to dbt-engineer for any task involving SQL changes, model implementation, seed data fixes, or applying code review feedback
- **Applications**: 27+ | **Success Rate**: Validated

### review_after_implementation ✓
- **Source**: routing-decisions.json (55 entries analyzed)
- **Graduated**: 2026-03-02
- **Description**: dbt-code-reviewer is consistently routed after dbt-engineer completes implementation work, forming the most common two-agent workflow chain
- **Routing Rule**: Always route to dbt-code-reviewer after dbt-engineer finishes implementation; route back to dbt-engineer if review finds issues
- **Applications**: 12+ | **Success Rate**: Validated

### warned_routing_mismatches ✓
- **Source**: routing-decisions.json (55 entries analyzed)
- **Graduated**: 2026-03-02
- **Description**: 3 routing decisions were "warned" — tasks sent to dbt-engineer that should have gone to dbt-code-reviewer (for review tasks) or data-architect (for schema/design changes like YTD window functions, model unions)
- **Routing Rule**: Tasks involving "review" should route to dbt-code-reviewer; tasks involving structural model changes or new aggregation patterns should route to data-architect first
- **Applications**: 3 warnings caught | **Success Rate**: Validated

## Candidates

(No candidate patterns yet)

## Expired

(No expired patterns)
