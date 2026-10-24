# NYC Taxi Platform - Snowflake + dbt + Airflow

```
data/incoming/yellow_tripdata_YYYY-MM.parquet
      |  (watchdog)
      v
file_watcher.py --REST--> Airflow DAG: nyc_taxi_pipeline
   load_to_bronze -> NYC_TAXI_DB.BRONZE.YELLOW_TRIPS_RAW   (as received)
   dbt seed       -> SILVER.TAXI_ZONE_LOOKUP
   dbt silver     -> SILVER.STG_YELLOW_TRIPS (incremental), SILVER.DIM_ZONES
   dbt gold       -> GOLD.DAILY_TRIPS / MONTHLY_SUMMARY / HOURLY_DEMAND /
                          ZONE_PERFORMANCE / PAYMENT_ANALYSIS / ROUTE_POPULARITY /
                          DATA_QUALITY_BY_FILE
   insights       -> reports/dashboard.png + reports/summary.md
```

## Run order
1. Snowflake: run `snowflake/01_setup.sql` in Snowsight (as ACCOUNTADMIN).
2. Edit `.env` -> set `SNOWFLAKE_ACCOUNT`.
3. `uv sync`
4. `cd dbt_project && uv run --env-file ../.env dbt debug --profiles-dir .`
5. `docker compose up --build -d`   -> http://localhost:8080  (admin / admin)
6. `uv run python ingestion/file_watcher.py`
7. `uv run python scripts/download_taxi_data.py --zones`
8. `uv run python scripts/download_taxi_data.py --year 2025 --months 1`
