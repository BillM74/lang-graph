---
name: snowflake-optimization
description: Snowflake performance tuning and cost optimization. Use when: "query is slow", "optimize performance", "reduce costs", "warehouse sizing", "clustering strategy", "this takes too long", "expensive query", "how to speed up", "performance issue", "costs too much", "slow build"
compatibility: Requires snowflake-mcp server connection
metadata:
  mcp-server: snowflake-mcp
  author: Analytics Team
  version: 2.0.0
---

# Snowflake Optimization

Quick reference for performance tuning and cost optimization in Snowflake.

## Quick Wins Checklist

Start here for immediate improvements:

- [ ] **Explicit columns** - Replace `SELECT *` with specific columns (20-80% faster)
- [ ] **Date filters** - Add `WHERE date >= 'YYYY-MM-DD'` to large table queries
- [ ] **Clustering** - Add cluster keys to tables > 1TB
- [ ] **Incremental models** - Use for large, frequently-updated tables (5-10x faster)
- [ ] **Auto-suspend** - Set to 60 seconds (50-80% cost reduction)
- [ ] **Right-size warehouses** - Don't use X-Large when Medium works
- [ ] **Transient tables** - Use for staging/intermediate models (50% storage savings)

## Investigation Workflow

When facing performance or cost issues:

1. **Profile the query** → Run `scripts/query-profile-analyzer.sql`
2. **Identify bottleneck** → Check bytes scanned, spillage, partition pruning
3. **Apply fix** → Use decision tree below
4. **Measure improvement** → A/B comparison (before/after metrics)
5. **Document** → Record in `.claude/memory/baselines/`

## MCP Tools Available

| Tool | Purpose | Quick Use |
|------|---------|-----------|
| `mcp__snowflake__run_snowflake_query` | Execute diagnostic SQL | Run scripts from `scripts/` |
| `mcp__snowflake__describe_object` | Inspect structure | Check clustering keys, columns |
| `mcp__snowflake__list_objects` | Find tables/warehouses | Discover objects |
| `mcp__dbt__show` | Preview dbt SQL | Test changes before full run |
| `mcp__dbt__build` | Run optimized models | Execute improvements |

**Diagnostic scripts** in `scripts/`:
- `query-profile-analyzer.sql` - Find expensive queries
- `clustering-health-check.sql` - Check clustering status
- `cost-breakdown-query.sql` - Daily credit usage
- `warehouse-spillage-check.sql` - Detect undersized warehouses

## Performance Decision Tree

```
What's the symptom?
├─ Query is slow
│  ├─ Full table scan → Add clustering (see references/clustering-strategies.md)
│  ├─ Large bytes scanned → Use explicit columns, add filters
│  ├─ Spillage to disk → Increase warehouse size (see references/warehouse-sizing.md)
│  ├─ Slow joins → Filter before joining (see references/query-optimization-patterns.md)
│  └─ Complex window functions → Add PARTITION BY, use QUALIFY
│
├─ dbt build is slow
│  ├─ Large tables as views → Change to table/incremental
│  ├─ Full refresh on large tables → Use incremental strategy
│  ├─ Too few threads → Increase dbt threads (8-12 for Medium warehouse)
│  └─ Models run sequentially → Check dependencies, enable parallelism
│
└─ Costs are high
   ├─ Idle warehouses → Enable auto-suspend (60s)
   ├─ Oversized warehouses → Right-size (see references/warehouse-sizing.md)
   ├─ Storage costs → Use transient tables, minimize Time Travel
   └─ Expensive queries → Optimize query patterns (see references/cost-analysis.md)
```

## Common Scenarios → Quick Solutions

| Scenario | Solution | Expected Impact |
|----------|----------|-----------------|
| Query scans full table | Add clustering on date column | 3-5x faster |
| Large join is slow | Filter in CTEs before joining | 2-4x faster |
| dbt build takes > 30 min | Add incremental strategy | 5-10x faster |
| SELECT * on wide table | List specific columns | 20-80% faster |
| Warehouse always running | Set auto-suspend to 60s | 50-80% cost reduction |
| Spillage to disk | Increase warehouse by one size | 2-3x faster |

## Detailed Guides

For comprehensive coverage, see the `references/` directory:

### Performance Optimization
- **[Clustering Strategies](references/clustering-strategies.md)**
  - When to cluster (> 1TB tables)
  - Choosing clustering keys (date, high-cardinality columns)
  - Monitoring clustering health
  - dbt clustering configuration

- **[Query Optimization Patterns](references/query-optimization-patterns.md)**
  - Filter before joining
  - Use QUALIFY for window functions
  - Avoid SELECT *
  - Efficient aggregations
  - Snowflake-specific patterns (FLATTEN, IFF, TRY_CAST)

### Cost Optimization
- **[Warehouse Sizing](references/warehouse-sizing.md)**
  - Right-sizing decision tree
  - Auto-suspend & auto-resume
  - Multi-cluster warehouses
  - Workload separation
  - dbt thread optimization

- **[Cost Analysis](references/cost-analysis.md)**
  - Cost structure (compute, storage, cloud services)
  - Cost monitoring queries
  - Resource monitors
  - Transient tables
  - ROI calculation framework

## Materialization Strategy

Quick decision guide:

| Data Size | Query Frequency | Complexity | Recommended | dbt Config |
|-----------|----------------|------------|-------------|------------|
| < 1GB | Any | Simple | View | `materialized='view'` |
| < 1GB | High | Complex | Table | `materialized='table'` |
| > 1GB | Any | Any | Table | `materialized='table'` |
| > 10GB | Any | Any | Incremental | `materialized='incremental'` |

### dbt Incremental Config

```sql
{{
    config(
        materialized='incremental',
        unique_key='order_id',
        incremental_strategy='merge',  -- or 'append', 'delete+insert'
        cluster_by=['date_month', 'customer_segment'],
        transient=true
    )
}}

SELECT * FROM {{ ref('source') }}

{% if is_incremental() %}
    WHERE updated_at > (SELECT MAX(updated_at) FROM {{ this }})
{% endif %}
```

## Clustering Quick Reference

**When to cluster**: Tables > 1TB, frequent filters on specific columns

**Good clustering keys**:
1. Date columns (most selective)
2. High-cardinality categories
3. Frequently filtered columns

**dbt config**:
```sql
{{ config(cluster_by=['date_month', 'customer_segment']) }}
```

**Check health**: Run `scripts/clustering-health-check.sql`

**Details**: See [references/clustering-strategies.md](references/clustering-strategies.md)

## Warehouse Sizing Quick Reference

| Size | Credits/Hour | Use Case |
|------|--------------|----------|
| X-Small | 1 | Development, small queries |
| Small | 2 | Light production (< 100GB) |
| Medium | 4 | **Standard production** (sweet spot) |
| Large | 8 | Complex queries (> 1TB) |
| X-Large | 16 | Heavy transformations |

**Auto-suspend recommended**: 60 seconds for ETL, 300 seconds for BI

**Details**: See [references/warehouse-sizing.md](references/warehouse-sizing.md)

## Cost Optimization Quick Reference

**Biggest cost savers**:
1. **Auto-suspend** (50-80% reduction) - 1 minute config change
2. **Right-sizing** (30-75% reduction) - Match warehouse to workload
3. **Transient tables** (50% storage) - dbt config change
4. **Incremental models** (90% reduction) - For large tables
5. **Clustering** (75% less compute) - Better partition pruning

**Run daily**: `scripts/cost-breakdown-query.sql` to track spending

**Details**: See [references/cost-analysis.md](references/cost-analysis.md)

## Troubleshooting

### Query is slow despite optimizations

**Not a query issue**. Check:
1. Is table clustered properly? (Run `scripts/clustering-health-check.sql`)
2. Is warehouse sized correctly? (Check for spillage)
3. Is there contention? (Multiple users on same warehouse)

### Costs increased suddenly

**Investigation steps**:
1. Run `scripts/cost-breakdown-query.sql` - which warehouse?
2. Check `warehouse_metering_history` - when did it spike?
3. Find expensive queries - run `scripts/query-profile-analyzer.sql`
4. Check auto-suspend settings - still configured?

### Clustering not helping

**Possible causes**:
1. Queries don't filter on clustered columns
2. Clustering key order wrong
3. Table too small to benefit (< 1TB)

**Solution**: Review query patterns, adjust clustering key

## Success Metrics

Optimization is successful when:
- ✅ Query runtime reduced by > 30%
- ✅ dbt build time reduced
- ✅ Snowflake costs decreased
- ✅ No spillage to disk
- ✅ Good partition pruning (< 20% partitions scanned)
- ✅ Data quality maintained

## Memory Integration

### Before Optimizing

Check baselines:
```
.claude/memory/baselines/query-times.json
.claude/memory/patterns/successful-optimizations.json
```

Query actual metrics via MCP: `scripts/query-profile-analyzer.sql`

### After Optimizing

**Mandatory A/B comparison** - Record before/after:
- Query duration (seconds)
- Bytes scanned (GB)
- Credits used
- Optimization applied
- Date

**Document in**:
```
.claude/memory/baselines/query-times.json
```

### Optimization Playbook (Project-Specific)

| Issue | Optimization | Typical Improvement |
|-------|-------------|---------------------|
| Full table scan on date | Cluster by date_month | 3-5x faster |
| Large joins | Filter before joining | 2-4x faster |
| SELECT * | Explicit columns | 20-40% faster |
| No incremental | Add incremental strategy | 5-10x faster |
| Missing date filter | Add WHERE date >= ... | 3-5x faster |

## Related Skills

- **incremental-strategies** - Deep dive on dbt incremental models
- **sql-code-quality** - SQL patterns and anti-patterns
- **dbt-testing** - Test performance optimizations

## Quick Command Reference

```bash
# Profile dbt run
dbt run --profile --threads 8

# Run only changed models
dbt run --select state:modified+

# Run specific model with dependencies
dbt run --select +revenue_metrics

# Check query execution
dbt show --select model_name --limit 10
```

---

**Pro tip**: Start with Quick Wins Checklist → Run diagnostic scripts → Apply targeted fix → Measure improvement → Document learning.
