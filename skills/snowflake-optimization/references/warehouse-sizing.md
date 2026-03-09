# Warehouse Sizing Guide

Comprehensive guide to right-sizing Snowflake warehouses for performance and cost optimization.

## Warehouse Size Guidelines

| Size | Credits/Hour | Use Case | Typical Workload |
|------|--------------|----------|------------------|
| X-Small | 1 | Development, small queries | < 10GB data, simple transformations |
| Small | 2 | Light production | < 100GB, basic analytics |
| Medium | 4 | Standard production | < 500GB, typical dbt builds |
| Large | 8 | Complex queries | > 1TB, complex joins |
| X-Large | 16 | Heavy transformations | Very large joins, aggregations |
| 2X-Large | 32 | Data science, ML | Massive data processing |
| 3X-Large | 64 | Rare, specialized | Extreme compute needs |
| 4X-Large | 128 | Very rare | Largest possible workloads |

## Right-Sizing Decision Tree

```
Does the query spill to disk?
├── Yes → Increase warehouse size
└── No
    └── Does the query finish in acceptable time?
        ├── Yes → Keep current size (or consider reducing)
        └── No
            └── Is it compute-bound or I/O-bound?
                ├── Compute → Increase size
                └── I/O → Consider clustering, not size
```

## Detecting Undersized Warehouses

### Signs of Undersized Warehouse

1. **Spillage to disk** - Most critical indicator
2. **Long queue times** - Queries waiting for resources
3. **Slow complex joins** - Multi-table joins taking > 5 minutes
4. **High memory pressure** - OOM errors

### Check for Spillage

Use the `warehouse-spillage-check.sql` script from `scripts/`:

```sql
SELECT
    query_id,
    warehouse_name,
    warehouse_size,
    bytes_spilled_to_local_storage / 1e9 AS gb_local_spill,
    bytes_spilled_to_remote_storage / 1e9 AS gb_remote_spill,
    execution_time / 1000 AS seconds
FROM snowflake.account_usage.query_history
WHERE start_time >= DATEADD(day, -7, CURRENT_TIMESTAMP())
    AND (bytes_spilled_to_local_storage > 0
         OR bytes_spilled_to_remote_storage > 0)
ORDER BY bytes_spilled_to_remote_storage DESC;
```

**Action**: If you see consistent spillage, increase warehouse size by one level.

## Multi-Cluster Warehouses

### When to Use

Enable multi-cluster for:
- **Variable workloads** - Peak and off-peak hours
- **Concurrent users** - Multiple teams using same warehouse
- **BI dashboards** - Unpredictable query patterns

### Configuration

```sql
ALTER WAREHOUSE analytics_wh SET
    min_cluster_count = 1
    max_cluster_count = 3
    scaling_policy = 'STANDARD';  -- or 'ECONOMY'
```

### Scaling Policies

| Policy | Scale Up Speed | Scale Down Speed | Best For |
|--------|---------------|------------------|----------|
| STANDARD | Fast (< 1 min) | Fast | Variable workloads, good performance |
| ECONOMY | Slow (~10 min) | Slow | Predictable workloads, cost-sensitive |

**Recommendation**: Start with STANDARD, switch to ECONOMY only if costs are excessive.

## Auto-Suspend & Auto-Resume

### Auto-Suspend Configuration

```sql
ALTER WAREHOUSE analytics_wh SET
    auto_suspend = 60        -- seconds
    auto_resume = true;
```

### Recommended Settings by Workload

| Workload Type | Auto-Suspend | Rationale |
|--------------|--------------|-----------|
| Development | 60 seconds | Minimize costs, resume quickly |
| dbt/ETL Jobs | 60 seconds | Jobs complete, then suspend |
| BI Dashboards | 300 seconds (5 min) | Keep alive between queries |
| Production API | 300-600 seconds | Balance latency vs cost |
| Ad-hoc Analysis | 120 seconds | User might run multiple queries |

**Key Insight**: Snowflake resume is typically < 5 seconds, so aggressive auto-suspend (60s) rarely impacts user experience.

## Warehouse Workload Separation

### Recommended Strategy

Create separate warehouses for different workload types:

```
📊 ANALYTICS_WH (Medium)
   - Analyst queries
   - Ad-hoc exploration
   - Auto-suspend: 120s

🔧 ETL_WH (Large)
   - dbt builds
   - Data transformations
   - Auto-suspend: 60s

📈 DASHBOARD_WH (Small-Medium)
   - Power BI queries
   - Scheduled refreshes
   - Multi-cluster: 1-3
   - Auto-suspend: 300s

💻 DEV_WH (X-Small)
   - Development work
   - Testing
   - Auto-suspend: 60s

🔬 DS_WH (X-Large)
   - Data science
   - ML workloads
   - Auto-suspend: 60s
```

### Benefits

✅ **Isolation** - One workload can't starve another
✅ **Cost attribution** - Clear cost by team/function
✅ **Right-sizing** - Each optimized for its workload
✅ **Performance** - No resource contention

## Cost Optimization Through Sizing

### Common Oversizing Scenarios

❌ **Using X-Large for simple queries**
- Problem: Paying 16 credits/hour for work an X-Small can do
- Solution: Right-size to Small or Medium
- Savings: 87-93% reduction in compute costs

❌ **No auto-suspend configured**
- Problem: Warehouse runs 24/7 even when idle
- Solution: Set auto-suspend to 60-120 seconds
- Savings: 50-80% reduction (depending on usage patterns)

❌ **Single warehouse for all workloads**
- Problem: Must size for peak load, even off-peak
- Solution: Separate warehouses by workload
- Savings: 30-50% through better utilization

### Sizing Experiment Approach

1. **Establish baseline**: Current size, query times, costs
2. **Make one change**: Increase or decrease by one size
3. **Measure for 1 week**: Compare performance and costs
4. **Decide**: Keep if improved, revert if degraded

**Example**:
- Current: Medium (4 credits/hour), dbt build takes 20 minutes
- Test: Large (8 credits/hour), dbt build takes 12 minutes
- Analysis: 2x cost, 40% faster → Not worth it unless time is critical
- Result: Stay on Medium

## dbt-Specific Sizing

### dbt Build Performance vs. Cost

| Warehouse | dbt Build Time | Cost per Build | Notes |
|-----------|---------------|----------------|-------|
| Small | 60 min | $0.40 | Cheap but slow |
| Medium | 30 min | $0.40 | Sweet spot |
| Large | 18 min | $0.48 | Faster, slightly more expensive |
| X-Large | 12 min | $0.64 | Diminishing returns |

**Recommendation**: Medium is typically the sweet spot for most dbt projects.

### Thread Count Optimization

Warehouse size and dbt threads should be balanced:

| Warehouse Size | Recommended Threads | Rationale |
|----------------|---------------------|-----------|
| X-Small | 4 | Limited compute |
| Small | 6-8 | Light parallelism |
| Medium | 8-12 | Good parallelism |
| Large | 12-16 | Heavy parallelism |
| X-Large+ | 16-24 | Maximum parallelism |

**From dbt docs**: Threads > 16 rarely provide additional benefit.

## Resource Monitors

Set spending limits to prevent runaway costs:

```sql
CREATE RESOURCE MONITOR monthly_limit
    WITH CREDIT_QUOTA = 1000
    TRIGGERS
        ON 75 PERCENT DO NOTIFY
        ON 90 PERCENT DO NOTIFY
        ON 100 PERCENT DO SUSPEND;

-- Assign to warehouse
ALTER WAREHOUSE analytics_wh SET RESOURCE_MONITOR = monthly_limit;
```

### Recommended Thresholds

| Threshold | Action | Use Case |
|-----------|--------|----------|
| 75% | Notify | Early warning |
| 90% | Notify + Review | Investigate high usage |
| 100% | Suspend | Hard limit (use cautiously) |
| 110% | Suspend immediately | Emergency brake |

## Monitoring & Alerts

### Check Warehouse Utilization

```sql
-- Warehouse activity last 7 days
SELECT
    warehouse_name,
    AVG(avg_running) AS avg_queries_running,
    AVG(avg_queued_load) AS avg_queued,
    SUM(credits_used) AS total_credits
FROM snowflake.account_usage.warehouse_load_history
WHERE start_time >= DATEADD(day, -7, CURRENT_TIMESTAMP())
GROUP BY 1
ORDER BY 4 DESC;
```

**Interpretation**:
- `avg_queries_running` close to 0 → Oversized or underutilized
- `avg_queued` > 1 → Undersized, enable multi-cluster
- High credits but low utilization → Auto-suspend not configured

## Common Patterns from This Project

Based on optimizations in this analytics project:

| Scenario | Original | Optimized | Result |
|----------|----------|-----------|--------|
| Development queries | Medium (overkill) | X-Small | 75% cost reduction |
| dbt nightly builds | Small (slow) | Medium | 40% faster, same cost |
| BI dashboard | Large (oversized) | Small + multi-cluster | 70% cost reduction |
| Analyst ad-hoc | No auto-suspend | 60s auto-suspend | 60% cost reduction |

## Troubleshooting

### Problem: Queries are slow despite large warehouse

**Not a sizing issue**. Check:
1. Query optimization (SELECT *, missing filters)
2. Clustering (poor partition pruning)
3. Materialization strategy (view vs table)

### Problem: High costs despite reasonable sizing

Check:
1. Auto-suspend configured?
2. Warehouse running idle overnight?
3. Multiple warehouses for same workload?

### Problem: Query queue times

Solutions:
1. Enable multi-cluster warehouses
2. Separate workloads to different warehouses
3. Increase max_cluster_count

### Problem: Inconsistent performance

Likely causes:
1. Warehouse auto-suspends between queries (increase timeout)
2. Multi-cluster scaling up (enable STANDARD policy)
3. Result cache misses (queries slightly different)
