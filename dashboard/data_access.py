
"""Read-only data access for the NYC Taxi dashboard."""

import pandas as pd
import streamlit as st

from common.snowflake_conn import get_connection

ROLE = "TRANSFORMER_ROLE"
WAREHOUSE = "TRANSFORM_WH"
SCHEMA = "GOLD"


@st.cache_data(ttl=300, show_spinner=False)
def load_gold_data(table_name: str) -> pd.DataFrame:
    """Load a Gold table and cache the result for five minutes."""

    allowed_tables = {
        "DAILY_TRIPS",
        "MONTHLY_SUMMARY",
        "HOURLY_DEMAND",
        "ZONE_PERFORMANCE",
        "ROUTE_POPULARITY",
        "PAYMENT_ANALYSIS",
        "DATA_QUALITY_BY_FILE",
    }

    if table_name not in allowed_tables:
        raise ValueError(f"Unsupported Gold table: {table_name}")

    connection = get_connection(
        role=ROLE,
        warehouse=WAREHOUSE,
        schema=SCHEMA,
    )

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f'SELECT * FROM NYC_TAXI_DB.GOLD."{table_name}"'
            )
            columns = [item[0].lower() for item in cursor.description]
            rows = cursor.fetchall()

        return pd.DataFrame(rows, columns=columns)
    finally:
        connection.close()
