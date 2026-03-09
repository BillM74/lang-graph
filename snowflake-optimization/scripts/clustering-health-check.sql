-- Clustering Health Check
-- Use with: mcp__snowflake__run_snowflake_query
--
-- Identifies tables that need reclustering
-- Lower depth is better (1-2 is ideal, > 4 needs attention)

SELECT
    table_catalog,
    table_schema,
    table_name,
    clustering_key,
    average_depth,
    average_overlaps,
    CASE
        WHEN average_depth <= 2 THEN '🟢 Healthy'
        WHEN average_depth <= 4 THEN '🟡 Monitor'
        ELSE '🔴 Needs Reclustering'
    END AS health_status
FROM snowflake.account_usage.tables
WHERE table_schema NOT IN ('INFORMATION_SCHEMA')
    AND clustering_key IS NOT NULL
    AND average_depth IS NOT NULL
ORDER BY average_depth DESC;

-- To check a specific table:
-- SELECT SYSTEM$CLUSTERING_INFORMATION('schema.table_name');
