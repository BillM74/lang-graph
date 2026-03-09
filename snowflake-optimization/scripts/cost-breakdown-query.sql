-- Cost Breakdown Query
-- Use with: mcp__snowflake__run_snowflake_query
--
-- Daily credit usage by warehouse for the last 30 days
-- Adjust the rate (currently $3 per credit) to match your contract

SELECT
    DATE_TRUNC('day', start_time) AS day,
    warehouse_name,
    SUM(credits_used) AS total_credits,
    SUM(credits_used) * 3 AS estimated_cost_usd,  -- Adjust rate as needed
    ROUND(AVG(credits_used), 2) AS avg_credits_per_query
FROM snowflake.account_usage.warehouse_metering_history
WHERE start_time >= DATEADD(day, -30, CURRENT_TIMESTAMP())
GROUP BY 1, 2
ORDER BY 1 DESC, 3 DESC;
