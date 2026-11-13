"""Reusable Telco ETL steps for Airflow task-level orchestration."""

import os

from sqlalchemy import text

from telco_pipeline import (
    execute_sql_file,
    finish_pipeline_run,
    get_engine,
    get_table_count,
    load_billing_raw_incremental,
    run_step,
    start_pipeline_run,
    upsert_billing_core_with_metrics,
    validate_billing,
    validate_billing_staging,
    validate_billing_summary_mart,
    validate_core,
    validate_enriched_customer_360_mart,
    validate_mart,
    validate_staging,
)

# Keep these names aligned with the original telco_pipeline.main().
STEP_NAMES = (
    "1. Transform Base STAGING",
    "2. Validate Base STAGING",
    "3. UPSERT Base CORE",
    "4. Validate Base CORE",
    "5. Incremental Billing RAW Load",
    "6. Transform Billing STAGING",
    "7. Validate Billing STAGING",
    "8. UPSERT Billing CORE",
    "9. Validate Billing Pipeline",
    "10. Build Customer 360 MART",
    "11. Validate Customer 360 MART",
    "12. Build Billing Summary MART",
    "13. Validate Billing Summary MART",
    "14. Build Enriched Customer 360 MART",
    "15. Validate Enriched Customer 360 MART",
)

BASE_STAGING_TABLES = (
    "staging.demographics",
    "staging.location",
    "staging.population",
    "staging.services",
    "staging.status",
)

BASE_CORE_TABLES = (
    "core.customer",
    "core.location",
    "core.population",
    "core.services",
    "core.customer_status",
)


def _safe_dev_engine():
    """Reject any accidental connection to the original Telco database."""
    if (
        os.environ.get("DB_HOST") != "telco-warehouse-dev"
        or os.environ.get("DB_NAME") != "telco_airflow_dev"
        or os.environ.get("DB_USER") != "telco_dev_user"
    ):
        raise RuntimeError(
            "Unsafe database target: expected "
            "telco_dev_user@telco-warehouse-dev/telco_airflow_dev"
        )
    if not os.environ.get("DB_PASSWORD"):
        raise RuntimeError("DB_PASSWORD is missing")
    return get_engine()


def create_airflow_pipeline_run() -> int:
    engine = _safe_dev_engine()
    try:
        run_id = int(start_pipeline_run(engine))
        print(f"Created Telco audit Run ID: {run_id}")
        return run_id
    finally:
        engine.dispose()


def run_airflow_etl_step(run_id: int, step_number: int) -> None:
    """Execute exactly one existing ETL step using the original audit wrapper."""
    if not 1 <= step_number <= len(STEP_NAMES):
        raise ValueError(f"Unknown Telco ETL step: {step_number}")

    engine = _safe_dev_engine()
    try:
        def count_tables(names):
            return sum(get_table_count(engine, name) for name in names)

        # Each entry matches the corresponding run_step() in telco_pipeline.main().
        steps = {
            1: (
                lambda: execute_sql_file(engine, "06_transform_staging.sql"),
                lambda _: count_tables(BASE_STAGING_TABLES),
            ),
            2: (lambda: validate_staging(engine), None),
            3: (
                lambda: execute_sql_file(engine, "25_upsert_base_core.sql"),
                lambda _: count_tables(BASE_CORE_TABLES),
            ),
            4: (lambda: validate_core(engine), None),
            5: (
                lambda: load_billing_raw_incremental(engine),
                lambda rows_loaded: rows_loaded,
            ),
            6: (
                lambda: execute_sql_file(engine, "20_transform_billing_staging.sql"),
                lambda _: get_table_count(engine, "staging.billing_transactions"),
            ),
            7: (lambda: validate_billing_staging(engine), None),
            8: (
                lambda: upsert_billing_core_with_metrics(engine),
                lambda metrics: metrics["rows_processed"],
            ),
            9: (lambda: validate_billing(engine), None),
            10: (
                lambda: execute_sql_file(engine, "12_create_customer_360_mart.sql"),
                lambda _: get_table_count(engine, "mart.customer_360"),
            ),
            11: (lambda: validate_mart(engine), None),
            12: (
                lambda: execute_sql_file(engine, "26_create_customer_billing_mart.sql"),
                lambda _: get_table_count(engine, "mart.customer_billing_summary"),
            ),
            13: (lambda: validate_billing_summary_mart(engine), None),
            14: (
                lambda: execute_sql_file(engine, "28_create_enriched_customer_360_mart.sql"),
                lambda _: get_table_count(engine, "mart.customer_360_enriched"),
            ),
            15: (lambda: validate_enriched_customer_360_mart(engine), None),
        }

        action, rows_processed_function = steps[step_number]
        run_step(
            engine,
            run_id,
            STEP_NAMES[step_number - 1],
            action,
            rows_processed_function,
        )
    finally:
        engine.dispose()


def transform_base_staging(run_id: int) -> None:
    """Backward-compatible alias for the first Airflow step."""
    run_airflow_etl_step(run_id, 1)


def validate_base_staging(run_id: int) -> None:
    """Convenience alias for the second Airflow step."""
    run_airflow_etl_step(run_id, 2)


def get_airflow_step_results(run_id: int) -> list[tuple[str, str]]:
    """Read recorded PostgreSQL audit outcomes for one pipeline run."""
    engine = _safe_dev_engine()
    try:
        with engine.connect() as connection:
            rows = connection.execute(
                text("""
                    SELECT step_name, status
                    FROM audit.pipeline_step
                    WHERE run_id = :run_id
                """),
                {"run_id": run_id},
            ).all()
        return [(str(name), str(status)) for name, status in rows]
    finally:
        engine.dispose()


def finalize_airflow_pipeline_run(
    run_id: int,
    status: str,
    error_message: str | None = None,
) -> None:
    if status not in ("SUCCESS", "FAILED"):
        raise ValueError(f"Invalid pipeline status: {status}")

    engine = _safe_dev_engine()
    try:
        finish_pipeline_run(
            engine,
            run_id,
            status,
            error_message=error_message,
        )
        print(f"Pipeline Run ID {run_id} finalized as {status}")
    finally:
        engine.dispose()
