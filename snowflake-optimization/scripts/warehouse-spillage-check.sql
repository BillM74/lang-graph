-- Warehouse Spillage Check
-- Use with: mcp__snowflake__run_snowflake_query
--
-- Finds queries with spillage to disk (indicates undersized warehouse)
-- Remote spillage is particularly expensive

SELECT
    query_id,
    warehouse_name,
    warehouse_size,
    bytes_spilled_to_local_storage / 1e9 AS gb_local_spill,
    bytes_spilled_to_remote_storage / 1e9 AS gb_remote_spill,
    execution_time / 1000 AS seconds,
    query_text
FROM snowflake.account_usage.query_history
WHERE start_time >= DATEADD(day, -7, CURRENT_TIMESTAMP())
    AND (bytes_spilled_to_local_storage > 0
         OR bytes_spilled_to_remote_storage > 0)
ORDER BY bytes_spilled_to_remote_storage DESC
LIMIT 50;
