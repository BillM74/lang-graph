"""
dbt operation tools for LangGraph agents.

These wrap dbt CLI commands and manifest parsing for use
as LangGraph tools that agents can invoke.
"""

import json
import subprocess
from functools import lru_cache
from pathlib import Path

from langchain_core.tools import tool


def _run_dbt_command(
    command: list[str],
    project_dir: str = ".",
    profiles_dir: str = "~/.dbt",
    capture_output: bool = True,
) -> dict:
    """Execute a dbt CLI command and return structured output."""
    full_command = [
        "dbt",
        *command,
        "--project-dir", project_dir,
        "--profiles-dir", profiles_dir,
    ]
    try:
        result = subprocess.run(
            full_command,
            capture_output=capture_output,
            text=True,
            timeout=600,
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout": "",
            "stderr": "Command timed out after 600 seconds",
            "returncode": -1,
        }
    except FileNotFoundError:
        return {
            "success": False,
            "stdout": "",
            "stderr": "dbt CLI not found. Ensure dbt is installed and on PATH.",
            "returncode": -1,
        }


def _load_manifest(project_dir: str = ".") -> dict:
    """Load and parse the dbt manifest. Cached by (project_dir, mtime).

    Raises FileNotFoundError if manifest doesn't exist.
    Raises json.JSONDecodeError if manifest is invalid.
    """
    manifest_path = Path(project_dir) / "target" / "manifest.json"
    # Use mtime for cache invalidation (new parse = new mtime)
    mtime = manifest_path.stat().st_mtime
    return _load_manifest_cached(str(manifest_path), mtime)


@lru_cache(maxsize=4)
def _load_manifest_cached(path: str, mtime: float) -> dict:
    """Cache-backed manifest loader keyed on path + mtime."""
    return json.loads(Path(path).read_text())


@tool
def dbt_build(
    select: str = "",
    exclude: str = "",
    full_refresh: bool = False,
    project_dir: str = ".",
    profiles_dir: str = "~/.dbt",
) -> dict:
    """Run dbt build (run + test) for selected models.

    Args:
        select: dbt selection syntax (e.g., 'model_name', '+model_name', 'tag:daily')
        exclude: Models to exclude from the build
        full_refresh: Force full refresh for incremental models
        project_dir: Path to dbt project directory
        profiles_dir: Path to dbt profiles directory
    """
    cmd = ["build"]
    if select:
        cmd.extend(["--select", select])
    if exclude:
        cmd.extend(["--exclude", exclude])
    if full_refresh:
        cmd.append("--full-refresh")
    return _run_dbt_command(cmd, project_dir, profiles_dir)


@tool
def dbt_compile(
    select: str = "",
    project_dir: str = ".",
    profiles_dir: str = "~/.dbt",
) -> dict:
    """Compile dbt models to check for SQL errors without executing.

    Args:
        select: dbt selection syntax for specific models
        project_dir: Path to dbt project directory
        profiles_dir: Path to dbt profiles directory
    """
    cmd = ["compile"]
    if select:
        cmd.extend(["--select", select])
    return _run_dbt_command(cmd, project_dir, profiles_dir)


@tool
def dbt_run(
    select: str = "",
    exclude: str = "",
    full_refresh: bool = False,
    project_dir: str = ".",
    profiles_dir: str = "~/.dbt",
) -> dict:
    """Run dbt models (materialize without testing).

    Args:
        select: dbt selection syntax
        exclude: Models to exclude
        full_refresh: Force full refresh for incremental models
        project_dir: Path to dbt project directory
        profiles_dir: Path to dbt profiles directory
    """
    cmd = ["run"]
    if select:
        cmd.extend(["--select", select])
    if exclude:
        cmd.extend(["--exclude", exclude])
    if full_refresh:
        cmd.append("--full-refresh")
    return _run_dbt_command(cmd, project_dir, profiles_dir)


@tool
def dbt_test(
    select: str = "",
    exclude: str = "",
    project_dir: str = ".",
    profiles_dir: str = "~/.dbt",
) -> dict:
    """Run dbt tests for selected models.

    Args:
        select: dbt selection syntax
        exclude: Tests to exclude
        project_dir: Path to dbt project directory
        profiles_dir: Path to dbt profiles directory
    """
    cmd = ["test"]
    if select:
        cmd.extend(["--select", select])
    if exclude:
        cmd.extend(["--exclude", exclude])
    return _run_dbt_command(cmd, project_dir, profiles_dir)


@tool
def dbt_parse(
    project_dir: str = ".",
    profiles_dir: str = "~/.dbt",
) -> dict:
    """Parse dbt project and generate manifest without running.

    Args:
        project_dir: Path to dbt project directory
        profiles_dir: Path to dbt profiles directory
    """
    return _run_dbt_command(["parse"], project_dir, profiles_dir)


@tool
def dbt_show(
    select: str,
    limit: int = 10,
    project_dir: str = ".",
    profiles_dir: str = "~/.dbt",
) -> dict:
    """Preview model output without materializing (dbt show).

    Args:
        select: Model to preview
        limit: Number of rows to show
        project_dir: Path to dbt project directory
        profiles_dir: Path to dbt profiles directory
    """
    cmd = ["show", "--select", select, "--limit", str(limit)]
    return _run_dbt_command(cmd, project_dir, profiles_dir)


@tool
def dbt_list_models(
    select: str = "",
    resource_type: str = "model",
    project_dir: str = ".",
    profiles_dir: str = "~/.dbt",
) -> dict:
    """List dbt resources matching selection criteria.

    Args:
        select: dbt selection syntax
        resource_type: Resource type (model, test, source, seed, snapshot)
        project_dir: Path to dbt project directory
        profiles_dir: Path to dbt profiles directory
    """
    cmd = ["list", "--resource-type", resource_type]
    if select:
        cmd.extend(["--select", select])
    return _run_dbt_command(cmd, project_dir, profiles_dir)


@tool
def dbt_get_lineage(
    model_name: str,
    project_dir: str = ".",
) -> dict:
    """Get upstream and downstream lineage for a dbt model from the manifest.

    Args:
        model_name: Name of the model to trace lineage for
        project_dir: Path to dbt project directory
    """
    try:
        manifest = _load_manifest(project_dir)
        nodes = manifest.get("nodes", {})

        # Find the target node
        target_key = None
        for key in nodes:
            if key.endswith(f".{model_name}"):
                target_key = key
                break

        if not target_key:
            return {"success": False, "error": f"Model '{model_name}' not found in manifest."}

        target_node = nodes[target_key]
        upstream = target_node.get("depends_on", {}).get("nodes", [])

        # Find downstream consumers
        downstream = [
            key for key, node in nodes.items()
            if target_key in node.get("depends_on", {}).get("nodes", [])
        ]

        return {
            "success": True,
            "model": model_name,
            "upstream": upstream,
            "downstream": downstream,
            "resource_type": target_node.get("resource_type"),
            "materialization": target_node.get("config", {}).get("materialized"),
            "schema": target_node.get("schema"),
            "database": target_node.get("database"),
        }
    except FileNotFoundError:
        return {"success": False, "error": "manifest.json not found. Run dbt parse first."}
    except (json.JSONDecodeError, KeyError) as e:
        return {"success": False, "error": f"Failed to parse manifest: {e}"}


@tool
def dbt_get_node_details(
    model_name: str,
    project_dir: str = ".",
) -> dict:
    """Get detailed information about a specific dbt node from the manifest.

    Args:
        model_name: Name of the model
        project_dir: Path to dbt project directory
    """
    try:
        manifest = _load_manifest(project_dir)
        nodes = manifest.get("nodes", {})

        for key, node in nodes.items():
            if key.endswith(f".{model_name}"):
                return {
                    "success": True,
                    "name": node.get("name"),
                    "resource_type": node.get("resource_type"),
                    "schema": node.get("schema"),
                    "database": node.get("database"),
                    "materialized": node.get("config", {}).get("materialized"),
                    "description": node.get("description", ""),
                    "columns": {
                        col_name: col_info.get("description", "")
                        for col_name, col_info in node.get("columns", {}).items()
                    },
                    "depends_on": node.get("depends_on", {}).get("nodes", []),
                    "tags": node.get("tags", []),
                    "raw_sql": node.get("raw_code", ""),
                    "compiled_sql": node.get("compiled_code", ""),
                }

        return {"success": False, "error": f"Model '{model_name}' not found in manifest."}
    except FileNotFoundError:
        return {"success": False, "error": "manifest.json not found. Run dbt parse first."}
    except (json.JSONDecodeError, KeyError) as e:
        return {"success": False, "error": f"Failed to parse manifest: {e}"}
