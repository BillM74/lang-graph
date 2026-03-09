"""
Configuration for LangGraph workflows.

Environment variables:
    ANTHROPIC_API_KEY: API key for Claude models
    SNOWFLAKE_ACCOUNT: Snowflake account identifier
    SNOWFLAKE_USER: Snowflake username
    SNOWFLAKE_PASSWORD: Snowflake password
    SNOWFLAKE_WAREHOUSE: Snowflake warehouse name
    SNOWFLAKE_DATABASE: Snowflake database name
    SNOWFLAKE_SCHEMA: Snowflake schema name
    DBT_PROJECT_DIR: Path to dbt project directory
    DBT_PROFILES_DIR: Path to dbt profiles directory
    DARK_FACTORY_MODE: Enable self-recovery mode (optional)
"""

import os
from dataclasses import dataclass, field
from functools import lru_cache

from langchain_anthropic import ChatAnthropic


@dataclass
class SnowflakeConfig:
    """Snowflake connection configuration from environment variables."""
    account: str = field(default_factory=lambda: os.environ.get("SNOWFLAKE_ACCOUNT", ""))
    user: str = field(default_factory=lambda: os.environ.get("SNOWFLAKE_USER", ""))
    password: str = field(default_factory=lambda: os.environ.get("SNOWFLAKE_PASSWORD", ""))
    warehouse: str = field(default_factory=lambda: os.environ.get("SNOWFLAKE_WAREHOUSE", ""))
    database: str = field(default_factory=lambda: os.environ.get("SNOWFLAKE_DATABASE", ""))
    schema: str = field(default_factory=lambda: os.environ.get("SNOWFLAKE_SCHEMA", ""))


@lru_cache(maxsize=4)
def get_model(model_name: str = "claude-sonnet-4-20250514") -> ChatAnthropic:
    """Get a cached ChatAnthropic model instance."""
    return ChatAnthropic(model=model_name, temperature=0)
