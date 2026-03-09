# LEARNED.md — dbt-testing

> Machine-generated from pattern data. Do not edit manually.
> Last updated: 2026-03-02

## Graduated

### unique_fan_out ✓
- **Source**: common-test-failures.json
- **Graduated**: 2026-03-02
- **Description**: Unique test fails due to fan-out joins without aggregation
- **Fix**: Add DISTINCT or ROW_NUMBER dedup before the join
- **Applications**: 5+ | **Success Rate**: Validated

### not_null_orphans ✓
- **Source**: common-test-failures.json
- **Graduated**: 2026-03-02
- **Description**: NULL FK values from LEFT JOINs to missing dimension records
- **Fix**: COALESCE or add 'Unknown' dimension record
- **Applications**: 5+ | **Success Rate**: Validated

### relationship_timing ✓
- **Source**: common-test-failures.json
- **Graduated**: 2026-03-02
- **Description**: FK not found in dimension due to load order, soft deletes, or type mismatch
- **Fix**: Adjust DAG order via ref(), check soft delete filters, cast types
- **Applications**: 5+ | **Success Rate**: Validated

### accepted_values_new ✓
- **Source**: common-test-failures.json
- **Graduated**: 2026-03-02
- **Description**: New source values not in accepted values list
- **Fix**: Add value to accepted list or normalize case
- **Applications**: 5+ | **Success Rate**: Validated

### missing_pk_tests ✓
- **Source**: common-test-failures.json
- **Graduated**: 2026-03-02
- **Description**: Model has no unique/not_null tests on primary key
- **Fix**: Add schema.yml entry immediately after creating model
- **Applications**: 5+ | **Success Rate**: Validated

## Candidates

(No candidate patterns yet)

## Expired

(No expired patterns)
