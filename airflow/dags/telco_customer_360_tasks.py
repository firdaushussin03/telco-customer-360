
"""Airflow 3 DAG: one task per step of the Telco Customer 360 pipeline."""

from airflow.sdk import dag, task


# Exactly 15 independently visible Airflow ETL tasks.
ETL_TASKS = (
    "transform_base_staging",
    "validate_base_staging",
    "upsert_base_core",
    "validate_base_core",
    "load_billing_raw_incremental",
    "transform_billing_staging",
    "validate_billing_staging",
    "upsert_billing_core",
    "validate_billing_pipeline",
    "build_customer_360_mart",
    "validate_customer_360_mart",
    "build_billing_summary_mart",
    "validate_billing_summary_mart",
    "build_enriched_customer_360_mart",
    "validate_enriched_customer_360_mart",
)


@dag(
    dag_id="telco_customer_360_tasks",
    description="Run and audit all 15 Telco Customer 360 ETL steps individually",
    schedule=None,
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 0},
    tags=["telco", "development", "phase-2"],
)
def telco_customer_360_tasks():

    # ========================================================
    # START PIPELINE
    # ========================================================

    @task(task_id="start_pipeline")
    def start_pipeline() -> int:

        import sys
        sys.path.insert(0, "/app/src")

        from telco_airflow_steps import (
            create_airflow_pipeline_run,
        )

        return create_airflow_pipeline_run()

    # ========================================================
    # EXECUTE INDIVIDUAL ETL STEP
    # ========================================================

    @task
    def execute_etl_step(
        audit_run_id: int,
        step_number: int,
    ) -> None:

        import sys
        sys.path.insert(0, "/app/src")

        from telco_airflow_steps import (
            run_airflow_etl_step,
        )

        run_airflow_etl_step(
            audit_run_id,
            step_number,
        )

    # ========================================================
    # FINALIZE PIPELINE
    # ========================================================

    @task(
        task_id="finalize_pipeline",
        trigger_rule="all_done",
    )
    def finalize_pipeline(audit_run_id: int) -> None:

        import sys
        sys.path.insert(0, "/app/src")

        from telco_airflow_steps import (
            STEP_NAMES,
            finalize_airflow_pipeline_run,
            get_airflow_step_results,
        )

        # Retrieve PostgreSQL audit results
        results = get_airflow_step_results(
            audit_run_id
        )

        expected = set(STEP_NAMES)

        completed_names = {
            name
            for name, status in results
            if status == "SUCCESS"
        }

        # All 15 expected steps must have succeeded.
        # Also reject duplicate or unexpected audit records.
        success = (
            len(results) == len(STEP_NAMES)
            and len(completed_names) == len(STEP_NAMES)
            and completed_names == expected
            and all(
                status == "SUCCESS"
                for _, status in results
            )
        )

        status = "SUCCESS" if success else "FAILED"

        error_message = None

        if not success:

            missing = sorted(
                expected - completed_names
            )

            errors = [
                f"{name}: {step_status}"
                for name, step_status in results
                if step_status != "SUCCESS"
            ]

            error_message = (
                f"Expected {len(STEP_NAMES)} successful steps; "
                f"found {len(completed_names)} successful distinct steps "
                f"and {len(results)} audit records. "
                f"Missing/unsuccessful: {missing}. "
                f"Failed records: {errors}."
            )

        # Update audit.pipeline_run in PostgreSQL
        finalize_airflow_pipeline_run(
            audit_run_id,
            status,
            error_message,
        )

        # Ensure Airflow also reports a failed pipeline
        if not success:
            raise RuntimeError(error_message)

        print(
            f"All {len(STEP_NAMES)} Telco steps succeeded "
            f"(Run ID {audit_run_id})."
        )

    # ========================================================
    # DEFINE TASK DEPENDENCIES
    # ========================================================

    # Create PostgreSQL pipeline audit record.
    # This returns an XComArg during DAG parsing.
    audit_run_id = start_pipeline()

    # Create 15 separate Airflow tasks.
    previous_task = None

    for number, task_id in enumerate(
        ETL_TASKS,
        start=1,
    ):

        current_task = execute_etl_step.override(
            task_id=task_id,
        )(
            audit_run_id,
            number,
        )

        # Connect each ETL task to the previous task.
        if previous_task is not None:
            previous_task >> current_task

        previous_task = current_task

    # Finalize after the ETL chain completes or fails.
    previous_task >> finalize_pipeline(audit_run_id)


# Register the DAG with Airflow
telco_customer_360_tasks()
