
# ============================================================
# TELCO CUSTOMER 360 - INITIALIZATION COORDINATOR
# File: 58_initialize_if_needed.py
#
# Purpose:
#   - Detect whether the database is fresh or already initialized
#   - Coordinate bootstrap and initial RAW ingestion
#   - Verify existing database initialization
#   - Stop when incomplete initialization is detected
# ============================================================

import os
import subprocess
import sys

from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


PROJECT_SCHEMAS = {
    "raw",
    "staging",
    "core",
    "mart",
    "audit",
}

REQUIRED_TABLES = {
    # RAW
    ("raw", "demographics"),
    ("raw", "location"),
    ("raw", "population"),
    ("raw", "services"),
    ("raw", "status"),
    ("raw", "billing_transactions"),

    # CORE
    ("core", "customer"),
    ("core", "population"),
    ("core", "location"),
    ("core", "services"),
    ("core", "customer_status"),
    ("core", "billing_transactions"),

    # AUDIT
    ("audit", "pipeline_run"),
    ("audit", "pipeline_step"),
    ("audit", "pipeline_watermark"),
    ("audit", "billing_quarantine"),
}

# ============================================================
# EXPECTED INITIAL CUSTOMER RAW ROW COUNTS
# ============================================================

EXPECTED_RAW_ROWS = {
    "demographics": 7043,
    "location": 7043,
    "population": 1671,
    "services": 7043,
    "status": 7043,
}

# ============================================================
# REQUIRED PIPELINE COLUMNS
# ============================================================

REQUIRED_COLUMNS = {
    # Pipeline audit
    ("audit", "pipeline_step", "rows_processed"),
    ("audit", "pipeline_step", "rows_inserted"),
    ("audit", "pipeline_step", "rows_updated"),
    ("audit", "pipeline_step", "rows_unchanged"),

    # Billing watermark
    ("audit", "pipeline_watermark", "last_watermark"),

    # Billing quarantine
    ("audit", "billing_quarantine", "raw_record"),
    ("audit", "billing_quarantine", "status"),
    ("audit", "billing_quarantine", "resolved_at"),
    ("audit", "billing_quarantine", "resolution_note"),

    # Billing RAW
    ("raw", "billing_transactions", "bill_id"),
    ("raw", "billing_transactions", "updated_at"),

    # Billing CORE
    ("core", "billing_transactions", "bill_id"),
    ("core", "billing_transactions", "customer_id"),
    ("core", "billing_transactions", "updated_at"),
}

def verify_required_tables(engine):

    with engine.connect() as connection:

        existing_tables = set(
            connection.execute(
                text("""
                    SELECT table_schema, table_name
                    FROM information_schema.tables
                    WHERE table_schema IN ('raw', 'core', 'audit')
                      AND table_type = 'BASE TABLE'
                """)
            ).all()
        )

    missing_tables = REQUIRED_TABLES - existing_tables

    if missing_tables:
        missing_names = [
            f"{schema}.{table}"
            for schema, table in sorted(missing_tables)
        ]

        raise RuntimeError(
            "Incomplete database initialization. Missing tables: "
            + ", ".join(missing_names)
        )

    print("All 16 required database tables exist.")

# ============================================================
# VERIFY INITIAL CUSTOMER RAW DATA
# ============================================================

def verify_initial_raw_data(engine):

    with engine.connect() as connection:

        for table_name, expected_count in EXPECTED_RAW_ROWS.items():

            actual_count = connection.execute(
                text(f"SELECT COUNT(*) FROM raw.{table_name}")
            ).scalar_one()

            if actual_count != expected_count:
                raise RuntimeError(
                    f"RAW data verification failed for raw.{table_name}. "
                    f"Expected {expected_count} rows, found {actual_count}."
                )

            print(
                f"raw.{table_name}: {actual_count} rows verified."
            )

    print("Initial customer RAW data verification passed.")
    
# ============================================================
# VERIFY BILLING WATERMARK
# ============================================================

def verify_billing_watermark(engine):

    with engine.connect() as connection:

        watermark = connection.execute(
            text("""
                SELECT last_watermark
                FROM audit.pipeline_watermark
                WHERE pipeline_name = :pipeline_name
                  AND source_name = :source_name
            """),
            {
                "pipeline_name": "telco_customer_360",
                "source_name": "billing_transactions",
            },
        ).scalar_one_or_none()

    if watermark is None:
        raise RuntimeError(
            "Initialization incomplete: "
            "billing watermark record is missing."
        )

    print(f"Billing watermark verified: {watermark}")

# ============================================================
# VERIFY REQUIRED DATABASE COLUMNS
# ============================================================

def verify_required_columns(engine):

    with engine.connect() as connection:

        existing_columns = set(
            connection.execute(
                text("""
                    SELECT
                        table_schema,
                        table_name,
                        column_name
                    FROM information_schema.columns
                    WHERE table_schema IN ('raw', 'core', 'audit')
                """)
            ).all()
        )

    missing_columns = REQUIRED_COLUMNS - existing_columns

    if missing_columns:
        missing_names = [
            f"{schema}.{table}.{column}"
            for schema, table, column in sorted(missing_columns)
        ]

        raise RuntimeError(
            "Incomplete database initialization. Missing columns: "
            + ", ".join(missing_names)
        )

    print("All critical pipeline columns verified.")

# ============================================================
# VERIFY SOURCE FILES BEFORE INITIALIZATION
# ============================================================

def verify_source_files():

    raw_dir = Path(__file__).resolve().parents[1] / "data" / "raw"

    required_files = [
        "Telco_customer_churn_demographics.xlsx",
        "Telco_customer_churn_location.xlsx",
        "Telco_customer_churn_population.xlsx",
        "Telco_customer_churn_services.xlsx",
        "Telco_customer_churn_status.xlsx",
    ]

    missing_files = [
        filename
        for filename in required_files
        if not (raw_dir / filename).is_file()
    ]

    if missing_files:
        raise FileNotFoundError(
            "Initialization stopped. Missing source files: "
            + ", ".join(missing_files)
        )

    print("All five Excel source files available.")

def main():

    required_vars = [
        "DB_HOST",
        "DB_PORT",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
    ]

    missing_vars = [
        var for var in required_vars
        if not os.getenv(var)
    ]

    if missing_vars:
        raise RuntimeError(
            "Missing database settings: "
            + ", ".join(missing_vars)
        )

    connection_url = URL.create(
        drivername="postgresql+psycopg2",
        username=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        host=os.environ["DB_HOST"],
        port=int(os.environ["DB_PORT"]),
        database=os.environ["DB_NAME"],
    )

    engine = create_engine(connection_url)

    try:
        with engine.connect() as connection:

            existing_schemas = set(
                connection.execute(
                    text("""
                        SELECT schema_name
                        FROM information_schema.schemata
                        WHERE schema_name IN (
                            'raw', 'staging', 'core', 'mart', 'audit'
                        )
                    """)
                ).scalars().all()
            )

        if not existing_schemas:

            print("Database state: FRESH")

            # Verify source files before creating any database objects
            verify_source_files()

            src_dir = Path(__file__).resolve().parent

            # Initialize database schemas and tables
            print("\nRunning database bootstrap...")

            subprocess.run(
                [
                    sys.executable,
                    str(src_dir / "57_bootstrap_database.py"),
                ],
                check=True,
            )

            # Load initial customer Excel datasets
            print("\nLoading initial customer RAW data...")

            subprocess.run(
                [
                    sys.executable,
                    str(src_dir / "03_load_raw_data.py"),
                ],
                check=True,
            )

            print("\nDatabase initialization completed successfully.")

        elif existing_schemas == PROJECT_SCHEMAS:

            verify_required_tables(engine)
            
            verify_required_columns(engine)
            
            verify_initial_raw_data(engine)
            
            verify_billing_watermark(engine)

            print(
                "Database state: SCHEMAS, TABLES, RAW DATA "
                "AND BILLING WATERMARK VERIFIED. "
                "Further structure checks are still needed."
            )

        else:
            raise RuntimeError(
                "Partial database initialization detected: "
                + ", ".join(sorted(existing_schemas))
            )

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
