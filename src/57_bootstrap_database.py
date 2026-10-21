# ============================================================
# TELCO CUSTOMER 360 - DATABASE BOOTSTRAP
# File: 57_bootstrap_database.py
#
# Purpose:
#   - Initialize a fresh PostgreSQL database
#   - Create the required schemas and tables
#   - Prepare the database for initial RAW ingestion
# ============================================================

import os
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


# ============================================================
# 1. PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = PROJECT_ROOT / "sql"


# ============================================================
# 2. REQUIRED DATABASE SCHEMAS
# ============================================================

SCHEMAS = [
    "raw",
    "staging",
    "core",
    "mart",
    "audit",
]


# ============================================================
# 3. SQL INITIALIZATION ORDER
# ============================================================

SETUP_SCRIPTS = [
    "02_create_raw_tables.sql",
    "17_create_billing_raw_table.sql",

    "08_create_core_tables.sql",
    "21_create_billing_core_table.sql",

    "14_create_pipeline_audit.sql",
    "30_extend_pipeline_step_audit.sql",
    "18_create_pipeline_watermark.sql",

    "33_create_billing_quarantine.sql",
    "35_add_billing_quarantine_resolution.sql",
]

# ============================================================
# 4. DATABASE CONNECTION
# ============================================================

def get_engine():
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
            "Missing database environment variables: "
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

    return create_engine(connection_url)

# ============================================================
# 5. FRESH DATABASE SAFETY CHECK
# ============================================================

def ensure_fresh_database(connection):

    existing_schemas = connection.execute(
        text("""
            SELECT schema_name
            FROM information_schema.schemata
            WHERE schema_name = ANY(:schemas)
            ORDER BY schema_name
        """),
        {"schemas": SCHEMAS},
    ).scalars().all()

    if existing_schemas:
        raise RuntimeError(
            "Bootstrap stopped! Existing project schemas detected: "
            + ", ".join(existing_schemas)
            + ". Please use a new, empty database."
        )

    print("Fresh database check passed.")
    
    # ============================================================
# 6. CREATE DATABASE SCHEMAS
# ============================================================

def create_schemas(connection):

    print("\nCreating database schemas...")

    for schema in SCHEMAS:

        connection.execute(
            text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
        )

        print(f"Schema ready: {schema}")

    print("All database schemas created successfully.")
    
# ============================================================
# 7. EXECUTE SQL INITIALIZATION SCRIPTS
# ============================================================

def execute_setup_scripts(connection):

    print("\nChecking SQL initialization files...")

    # Verify that every required SQL file exists.
    for script_name in SETUP_SCRIPTS:

        sql_path = SQL_DIR / script_name

        if not sql_path.is_file():
            raise FileNotFoundError(
                f"SQL initialization file not found: {sql_path}"
            )

    print("All SQL initialization files found.")

    # Execute SQL scripts in the defined order.
    for script_name in SETUP_SCRIPTS:

        sql_path = SQL_DIR / script_name

        print(f"\nExecuting: {script_name}")

        sql_content = sql_path.read_text(
            encoding="utf-8-sig"
        )

        connection.exec_driver_sql(sql_content)

        print(f"Completed: {script_name}")

    print("\nAll SQL initialization scripts completed.")

# ============================================================
# 8. MAIN BOOTSTRAP EXECUTION
# ============================================================

def main():

    print("=" * 70)
    print("TELCO CUSTOMER 360 - DATABASE BOOTSTRAP")
    print("=" * 70)

    engine = get_engine()

    try:
        with engine.begin() as connection:

            # Step 1: Check for an existing warehouse
            ensure_fresh_database(connection)

            # Step 2: Create required schemas
            create_schemas(connection)

            # Step 3: Create required database tables
            execute_setup_scripts(connection)

        print("\nDATABASE BOOTSTRAP COMPLETED SUCCESSFULLY.")

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()