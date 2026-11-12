
# ============================================================
# TELCO CUSTOMER 360 - AIRFLOW ORCHESTRATION
# Phase 1: Run the existing ETL as one Airflow task
# ============================================================

import os
import subprocess
import sys

from airflow.sdk import dag, task


@dag(
    dag_id="telco_customer_360_pipeline",
    description="Execute the Telco Customer 360 ETL pipeline",
    schedule=None,
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 0},
    tags=["telco", "development"],
)
def telco_customer_360_pipeline():

    @task(task_id="run_telco_pipeline")
    def run_etl():

        # Safety check: only use our isolated development DB
        if (
            os.environ.get("DB_HOST") != "telco-warehouse-dev"
            or os.environ.get("DB_NAME") != "telco_airflow_dev"
        ):
            raise RuntimeError(
                "Unsafe database target: expected telco_airflow_dev"
            )

        if not os.environ.get("DB_PASSWORD"):
            raise RuntimeError("Database password is missing")

        # Execute the existing ETL pipeline
        subprocess.run(
            [
                sys.executable,
                "-u",
                "/app/src/15_run_pipeline.py",
            ],
            cwd="/app",
            check=True,
        )

    run_etl()


telco_customer_360_pipeline()
