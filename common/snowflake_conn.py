"""Single place that knows how to connect to Snowflake (key-pair auth)."""
import os
from pathlib import Path

import snowflake.connector

PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT", Path(__file__).resolve().parents[1]))
DATABASE = os.getenv("SNOWFLAKE_DATABASE", "NYC_TAXI_DB")


def get_connection(role: str, warehouse: str, schema: str | None = None):
    key_path = os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH", str(PROJECT_ROOT / "keys" / "rsa_key.p8"))
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        private_key_file=key_path,
        role=role,
        warehouse=warehouse,
        database=DATABASE,
        schema=schema,
    )
