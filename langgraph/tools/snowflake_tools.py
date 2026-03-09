"""
Snowflake operation tools for LangGraph agents.

These provide query execution and diagnostic capabilities
against Snowflake, used by performance-optimizer and other agents.
"""

from contextlib import contextmanager

from langchain_core.tools import tool

from ..config import SnowflakeConfig

# Snowflake connector is optional — tools degrade gracefully
try:
    import snowflake.connector

    SNOWFLAKE_AVAILABLE = True
except ImportError:
    SNOWFLAKE_AVAILABLE = False


_VALID_OBJECT_TYPES = frozenset({
    "TABLE", "VIEW", "SCHEMA", "DATABASE", "STAGE", "FILE FORMAT",
    "SEQUENCE", "PIPE", "STREAM", "TASK", "FUNCTION", "PROCEDURE",
})

_VALID_LIST_TYPES = frozenset({
    "TABLES", "VIEWS", "SCHEMAS", "DATABASES", "WAREHOUSES",
    "STAGES", "FILE FORMATS", "SEQUENCES", "PIPES", "STREAMS", "TASKS",
})


@contextmanager
def _snowflake_cursor():
    """Context manager that yields a Snowflake cursor with proper cleanup."""
    if not SNOWFLAKE_AVAILABLE:
        raise RuntimeError(
            "snowflake-connector-python is not installed. "
            "Install with: pip install snowflake-connector-python"
        )
    cfg = SnowflakeConfig()
    conn = snowflake.connector.connect(
        account=cfg.account,
        user=cfg.user,
        password=cfg.password,
        warehouse=cfg.warehouse,
        database=cfg.database,
        schema=cfg.schema,
    )
    try:
        cursor = conn.cursor()
        try:
            yield cursor
        finally:
            cursor.close()
    finally:
        conn.close()


def _fetch_results(cursor, limit: int = 100) -> dict:
    """Extract columns and rows from an executed cursor."""
    columns = [desc[0] for desc in cursor.description] if cursor.description else []
    rows = cursor.fetchmany(limit)
    return {
        "success": True,
        "columns": columns,
        "rows": [dict(zip(columns, row)) for row in rows],
        "row_count": len(rows),
    }


@tool
def run_snowflake_query(
    query: str,
    limit: int = 100,
) -> dict:
    """Execute a SQL query against Snowflake and return results.

    Args:
        query: SQL query to execute
        limit: Maximum number of rows to return
    """
    try:
        with _snowflake_cursor() as cursor:
            cursor.execute(query)
            return _fetch_results(cursor, limit)
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def describe_snowflake_object(
    object_type: str,
    object_name: str,
) -> dict:
    """Describe a Snowflake object (table, view, etc.).

    Args:
        object_type: Type of object (TABLE, VIEW, SCHEMA, DATABASE)
        object_name: Fully qualified name of the object
    """
    upper_type = object_type.upper()
    if upper_type not in _VALID_OBJECT_TYPES:
        return {"success": False, "error": f"Invalid object type: {object_type}"}

    # Validate object_name contains only safe characters
    if not all(c.isalnum() or c in "._" for c in object_name):
        return {"success": False, "error": f"Invalid object name: {object_name}"}

    try:
        with _snowflake_cursor() as cursor:
            cursor.execute(f"DESCRIBE {upper_type} {object_name}")
            result = _fetch_results(cursor, limit=500)
            result.update({"object_type": upper_type, "object_name": object_name})
            return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def list_snowflake_objects(
    object_type: str = "TABLES",
    database: str = "",
    schema: str = "",
    pattern: str = "",
    limit: int = 500,
) -> dict:
    """List Snowflake objects of a given type.

    Args:
        object_type: Type to list (TABLES, VIEWS, SCHEMAS, DATABASES, WAREHOUSES)
        database: Database to search in
        schema: Schema to search in
        pattern: LIKE pattern to filter results
        limit: Maximum number of objects to return
    """
    upper_type = object_type.upper()
    if upper_type not in _VALID_LIST_TYPES:
        return {"success": False, "error": f"Invalid object type: {object_type}"}

    try:
        with _snowflake_cursor() as cursor:
            query = f"SHOW {upper_type}"
            params = []

            # Scope qualifier (identifiers validated)
            if database and schema:
                if not all(c.isalnum() or c in "._" for c in database + schema):
                    return {"success": False, "error": "Invalid database/schema name"}
                query += f" IN {database}.{schema}"
            elif database:
                if not all(c.isalnum() or c in "._" for c in database):
                    return {"success": False, "error": "Invalid database name"}
                query += f" IN DATABASE {database}"

            if pattern:
                query += " LIKE %s"
                params.append(pattern)

            cursor.execute(query, params) if params else cursor.execute(query)
            result = _fetch_results(cursor, limit)
            result.update({"object_type": upper_type, "count": result["row_count"]})
            return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def query_profile_analysis(
    query_id: str = "",
    query_text: str = "",
    warehouse: str = "",
) -> dict:
    """Analyze query performance using Snowflake query history.

    Provide either a query_id or query_text to find and analyze.

    Args:
        query_id: Specific query ID to analyze
        query_text: Query text pattern to search for in history
        warehouse: Warehouse to filter query history by
    """
    sql = """
    SELECT
        query_id,
        query_text,
        warehouse_name,
        execution_status,
        total_elapsed_time / 1000 AS runtime_seconds,
        bytes_scanned,
        bytes_written,
        bytes_spilled_to_local_storage,
        bytes_spilled_to_remote_storage,
        partitions_scanned,
        partitions_total,
        rows_produced,
        credits_used_cloud_services,
        compilation_time / 1000 AS compile_seconds,
        execution_time / 1000 AS execute_seconds,
        queued_overload_time / 1000 AS queue_seconds
    FROM TABLE(information_schema.query_history(
        dateadd('hours', -24, current_timestamp()),
        current_timestamp(),
        100
    ))
    WHERE 1=1
    """
    params = []
    if query_id:
        sql += "\n    AND query_id = %s"
        params.append(query_id)
    if query_text:
        sql += "\n    AND query_text ILIKE %s"
        params.append(f"%{query_text}%")
    if warehouse:
        sql += "\n    AND warehouse_name = %s"
        params.append(warehouse)
    sql += "\n    ORDER BY total_elapsed_time DESC\n    LIMIT 10"

    try:
        with _snowflake_cursor() as cursor:
            cursor.execute(sql, params) if params else cursor.execute(sql)
            return _fetch_results(cursor, limit=10)
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def clustering_health_check(
    table_name: str,
) -> dict:
    """Check clustering health for a Snowflake table.

    Args:
        table_name: Fully qualified table name to check
    """
    if not all(c.isalnum() or c in "._" for c in table_name):
        return {"success": False, "error": f"Invalid table name: {table_name}"}

    sql = f"""
    SELECT
        '{table_name}' AS table_name,
        system$clustering_information('{table_name}') AS clustering_info
    """
    return run_snowflake_query.invoke({"query": sql, "limit": 1})


@tool
def warehouse_spillage_check(
    warehouse_name: str = "",
    hours_back: int = 24,
) -> dict:
    """Check for warehouse spillage (memory overflow to disk/remote).

    Args:
        warehouse_name: Warehouse to check (empty for all)
        hours_back: Number of hours to look back
    """
    sql = f"""
    SELECT
        warehouse_name,
        COUNT(*) AS query_count,
        SUM(bytes_spilled_to_local_storage) AS total_local_spill_bytes,
        SUM(bytes_spilled_to_remote_storage) AS total_remote_spill_bytes,
        AVG(total_elapsed_time) / 1000 AS avg_runtime_seconds,
        MAX(total_elapsed_time) / 1000 AS max_runtime_seconds
    FROM TABLE(information_schema.query_history(
        dateadd('hours', -{int(hours_back)}, current_timestamp()),
        current_timestamp(),
        1000
    ))
    WHERE (bytes_spilled_to_local_storage > 0 OR bytes_spilled_to_remote_storage > 0)
    """
    params = []
    if warehouse_name:
        sql += "\n    AND warehouse_name = %s"
        params.append(warehouse_name)
    sql += "\n    GROUP BY warehouse_name\n    ORDER BY total_remote_spill_bytes DESC"

    try:
        with _snowflake_cursor() as cursor:
            cursor.execute(sql, params) if params else cursor.execute(sql)
            return _fetch_results(cursor, limit=20)
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def cost_breakdown(
    days_back: int = 30,
) -> dict:
    """Get Snowflake cost breakdown by warehouse over recent period.

    Args:
        days_back: Number of days to analyze
    """
    sql = f"""
    SELECT
        warehouse_name,
        COUNT(*) AS query_count,
        SUM(credits_used_cloud_services) AS total_credits,
        AVG(total_elapsed_time) / 1000 AS avg_runtime_seconds,
        SUM(bytes_scanned) AS total_bytes_scanned,
        SUM(bytes_spilled_to_remote_storage) AS total_remote_spill
    FROM snowflake.account_usage.query_history
    WHERE start_time >= dateadd('day', -{int(days_back)}, current_timestamp())
        AND warehouse_name IS NOT NULL
    GROUP BY warehouse_name
    ORDER BY total_credits DESC
    """
    return run_snowflake_query.invoke({"query": sql, "limit": 50})
