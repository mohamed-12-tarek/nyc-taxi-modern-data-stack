
"""
nyc_taxi_pipeline

load_to_bronze -> dbt_seed -> dbt_run_silver -> dbt_test_silver
               -> dbt_run_gold -> dbt_test_gold -> generate_insights

Triggered by the folder watcher (REST API) with:
    conf = {"file_path": "data/incoming/<file>.parquet"}

Manual trigger with no conf:
    Loads every .parquet file in data/incoming.
"""

from datetime import timedelta
import subprocess

from airflow.sdk import dag, task, get_current_context

PY = "/home/airflow/venv/bin/python"
DBT = "/home/airflow/venv/bin/dbt"
PROJECT = "/opt/project"
DBT_DIR = f"{PROJECT}/dbt_project"


default_args = {
    "owner": "data-eng",
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
    "execution_timeout": timedelta(hours=2),
}


def run_command(command: list[str], cwd: str) -> None:
    subprocess.run(
        command,
        cwd=cwd,
        check=True,
    )


@dag(
    dag_id="nyc_taxi_pipeline",
    description="TLC Parquet -> Snowflake Bronze -> dbt Silver/Gold -> insights",
    start_date=__import__("datetime").datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    default_args=default_args,
    tags=["snowflake", "dbt", "medallion", "nyc-taxi"],
)
def nyc_taxi_pipeline():

    @task
    def load_to_bronze():
        context = get_current_context()
        dag_run = context.get("dag_run")
        conf = (dag_run.conf or {}) if dag_run else {}
        file_path = conf.get("file_path", "")

        command = [
            PY,
            "ingestion/load_to_snowflake.py",
        ]

        if file_path:
            command.extend(["--file", file_path])

        run_command(command, cwd=PROJECT)

    @task
    def dbt_seed_zones():
        run_command(
            [DBT, "seed", "--profiles-dir", "."],
            cwd=DBT_DIR,
        )

    @task
    def dbt_run_silver():
        run_command(
            [DBT, "run", "--select", "silver", "--profiles-dir", "."],
            cwd=DBT_DIR,
        )

    @task
    def dbt_test_silver():
        run_command(
            [DBT, "test", "--select", "silver", "--profiles-dir", "."],
            cwd=DBT_DIR,
        )

    @task
    def dbt_run_gold():
        run_command(
            [DBT, "run", "--select", "gold", "--profiles-dir", "."],
            cwd=DBT_DIR,
        )

    @task
    def dbt_test_gold():
        run_command(
            [DBT, "test", "--select", "gold", "--profiles-dir", "."],
            cwd=DBT_DIR,
        )

    @task
    def generate_insights():
        run_command(
            [PY, "insights/generate_insights.py"],
            cwd=PROJECT,
        )

    bronze = load_to_bronze()
    seed = dbt_seed_zones()
    silver = dbt_run_silver()
    test_silver = dbt_test_silver()
    gold = dbt_run_gold()
    test_gold = dbt_test_gold()
    insights = generate_insights()

    bronze >> seed >> silver >> test_silver >> gold >> test_gold >> insights


nyc_taxi_pipeline()
