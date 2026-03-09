-- Test Failure Inspection Queries
-- Use these to investigate failing tests in Snowflake

-- 1. List all test failure tables
SHOW TABLES IN dbt_test_failures;

-- 2. Generic test failure inspection template
-- Replace {test_failure_table} with actual table name from SHOW TABLES
SELECT *
FROM dbt_test_failures.{test_failure_table}
LIMIT 100;

-- 3. Count failures over time (for recurring issues)
SELECT
    DATE_TRUNC('day', dbt_updated_at) AS failure_date,
    COUNT(*) as failure_count
FROM dbt_test_failures.{test_failure_table}
GROUP BY 1
ORDER BY 1 DESC;

-- 4. Most common failing values (for unique/accepted_values tests)
SELECT
    column_name,
    COUNT(*) as occurrence_count
FROM dbt_test_failures.{test_failure_table}
GROUP BY 1
ORDER BY 2 DESC
LIMIT 20;

-- 5. Sample failing records with context
SELECT *
FROM dbt_test_failures.{test_failure_table}
ORDER BY dbt_updated_at DESC
LIMIT 10;

-- 6. Find duplicate records (unique test failures)
-- Assuming primary_key_column is the column being tested for uniqueness
SELECT
    primary_key_column,
    COUNT(*) as duplicate_count
FROM dbt_test_failures.{test_failure_table}
GROUP BY 1
HAVING COUNT(*) > 1
ORDER BY 2 DESC;

-- 7. Find NULL records (not_null test failures)
SELECT
    COUNT(*) as null_count,
    DATE_TRUNC('day', created_at) AS null_date
FROM {source_model}
WHERE {column_name} IS NULL
GROUP BY 2
ORDER BY 2 DESC;

-- 8. Find orphan records (relationship test failures)
-- Replace {child_table}, {parent_table}, {foreign_key}, {primary_key}
SELECT c.*
FROM {child_table} c
LEFT JOIN {parent_table} p
    ON c.{foreign_key} = p.{primary_key}
WHERE p.{primary_key} IS NULL
LIMIT 100;

-- 9. Find unexpected values (accepted_values test failures)
SELECT
    {column_name},
    COUNT(*) as occurrence_count
FROM {source_model}
WHERE {column_name} NOT IN ({expected_values})
GROUP BY 1
ORDER BY 2 DESC;

-- 10. Enable test failure storage (add to dbt_project.yml)
/*
tests:
  +store_failures: true
  +schema: dbt_test_failures
*/
