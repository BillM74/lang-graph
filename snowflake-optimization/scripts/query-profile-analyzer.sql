-- Query Profile Analyzer
-- Use with: mcp__snowflake__run_snowflake_query
--
-- Analyzes recent expensive queries to identify performance bottlenecks
-- Look for: bytes scanned vs bytes sent, partition pruning, spillage, join issues

SELECT
    query_id,
    user_name,
    warehouse_name,
    total_elapsed_time / 1000 AS seconds,
    bytes_scanned / 1e9 AS gb_scanned,
    partitions_scanned,
    partitions_total,
    CASE
        WHEN partitions_total > 0
        THEN (partitions_scanned::FLOAT / partitions_total) * 100
        ELSE NULL
    END AS partition_scan_pct,
    query_text
FROM table(information_schema.query_history())
WHERE start_time > DATEADD(day, -1, CURRENT_TIMESTAMP())
ORDER BY total_elapsed_time DESC
LIMIT 20;
