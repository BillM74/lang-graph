# LEARNED.md — snowflake-optimization

> Machine-generated from pattern data. Do not edit manually.
> Last updated: 2026-03-02

## Graduated

### clustering_date_range ✓
- **Source**: successful-optimizations.json
- **Graduated**: 2026-03-02
- **Description**: Large fact tables with date-range queries benefit from clustering on (date_column, high_cardinality_filter)
- **Fix**: Add CLUSTER BY (date_column, dimension_key) for tables > 1TB with date-range query patterns
- **Applications**: 5+ | **Success Rate**: Validated (3-10x query speedup)

### incremental_append_events ✓
- **Source**: successful-optimizations.json
- **Graduated**: 2026-03-02
- **Description**: Immutable event/activity streams should use incremental append strategy with timestamp filter
- **Fix**: Use `materialized='incremental', incremental_strategy='append'` with reliable timestamp column
- **Applications**: 5+ | **Success Rate**: Validated (10-100x faster builds)

### incremental_merge_facts ✓
- **Source**: successful-optimizations.json
- **Graduated**: 2026-03-02
- **Description**: Fact tables with late-arriving updates should use incremental merge strategy with unique_key
- **Fix**: Use `materialized='incremental', incremental_strategy='merge', unique_key='pk_column'` for sparse updates
- **Applications**: 5+ | **Success Rate**: Validated (5-20x faster builds)

### pre_filter_joins ✓
- **Source**: successful-optimizations.json
- **Graduated**: 2026-03-02
- **Description**: Joins between large and small tables are faster when the large table is filtered in a CTE first
- **Fix**: Move selective WHERE predicates into a CTE before the JOIN instead of filtering after
- **Applications**: 5+ | **Success Rate**: Validated (2-5x faster queries)

### warehouse_right_size ✓
- **Source**: successful-optimizations.json
- **Graduated**: 2026-03-02
- **Description**: Queries spilling to disk need warehouse size matched to data volume
- **Fix**: Use LARGE for 100GB-1TB scans, XLARGE for >1TB; check query profile for bytes spilled
- **Applications**: 5+ | **Success Rate**: Validated (2-4x faster, often cheaper)

## Candidates

(No candidate patterns yet)

## Expired

(No expired patterns)
