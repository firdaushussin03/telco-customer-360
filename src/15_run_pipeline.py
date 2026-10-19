import pandas as pd
import re
import os
from pathlib import Path
from getpass import getpass

from sqlalchemy import URL, create_engine, text


# ============================================================
# TELCO CUSTOMER 360 - PIPELINE ORCHESTRATOR
# File: 15_run_pipeline.py
#
# Purpose:
#   - Run the base customer warehouse pipeline
#   - Run incremental billing ingestion
#   - Transform and UPSERT billing data
#   - Validate each layer
#   - Record pipeline and step status in audit tables
# ============================================================


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = PROJECT_ROOT / "sql"

BILLING_SOURCE_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "billing_transactions.csv"
)

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "telco_project")
DB_USER = os.getenv("DB_USER", "postgres")

PIPELINE_NAME = "telco_customer_360"
BILLING_SOURCE_NAME = "billing_transactions"


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_engine():
    password = os.getenv("DB_PASSWORD") or getpass("PostgreSQL password: ")

    connection_url = URL.create(
        drivername="postgresql+psycopg2",
        username=DB_USER,
        password=password,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
    )

    return create_engine(connection_url)


# ============================================================
# SQL FILE EXECUTION
# ============================================================

def execute_sql_file(engine, filename):
    file_path = SQL_DIR / filename

    if not file_path.exists():
        raise FileNotFoundError(
            f"SQL file not found: {file_path}"
        )

    sql = file_path.read_text(encoding="utf-8")
    print(f"Executing SQL file: {file_path.resolve()}")

    connection = engine.raw_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(sql)

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


# ============================================================
# QUERY HELPERS
# ============================================================

def get_scalar(engine, query):
    with engine.connect() as connection:
        return connection.execute(
            text(query)
        ).scalar_one()


def get_table_count(engine, full_table_name):
    return get_scalar(
        engine,
        f"SELECT COUNT(*) FROM {full_table_name}"
    )


def assert_equal(actual, expected, message):
    if actual != expected:
        raise RuntimeError(
            f"{message}. Expected {expected}, got {actual}."
        )


def assert_zero(engine, query, message):
    result = get_scalar(engine, query)

    if result != 0:
        raise RuntimeError(
            f"{message}. Found {result} invalid rows."
        )


# ============================================================
# AUDIT FUNCTIONS
# ============================================================

def start_pipeline_run(engine):
    query = text("""
        INSERT INTO audit.pipeline_run (
            pipeline_name,
            status
        )
        VALUES (
            :pipeline_name,
            'RUNNING'
        )
        RETURNING run_id;
    """)

    with engine.begin() as connection:
        return connection.execute(
            query,
            {"pipeline_name": PIPELINE_NAME},
        ).scalar_one()


def finish_pipeline_run(
    engine,
    run_id,
    status,
    error_message=None,
):
    query = text("""
        UPDATE audit.pipeline_run
        SET
            finished_at = CURRENT_TIMESTAMP,
            status = :status,
            error_message = :error_message
        WHERE run_id = :run_id;
    """)

    with engine.begin() as connection:
        connection.execute(
            query,
            {
                "run_id": run_id,
                "status": status,
                "error_message": error_message,
            },
        )


def start_pipeline_step(
    engine,
    run_id,
    step_name,
):
    query = text("""
        INSERT INTO audit.pipeline_step (
            run_id,
            step_name,
            status
        )
        VALUES (
            :run_id,
            :step_name,
            'RUNNING'
        )
        RETURNING step_id;
    """)

    with engine.begin() as connection:
        return connection.execute(
            query,
            {
                "run_id": run_id,
                "step_name": step_name,
            },
        ).scalar_one()


def finish_pipeline_step(
    engine,
    step_id,
    status,
    rows_processed=None,
    error_message=None,
    rows_inserted=None,
    rows_updated=None,
    rows_unchanged=None,
):
    # The three new fields were added by
    # 30_extend_pipeline_step_audit.sql.
    query = text("""
        UPDATE audit.pipeline_step
        SET
            finished_at = CURRENT_TIMESTAMP,
            status = :status,
            rows_processed = :rows_processed,
            rows_inserted = :rows_inserted,
            rows_updated = :rows_updated,
            rows_unchanged = :rows_unchanged,
            error_message = :error_message
        WHERE step_id = :step_id;
    """)

    with engine.begin() as connection:
        connection.execute(
            query,
            {
                "step_id": step_id,
                "status": status,
                "rows_processed": rows_processed,
                "rows_inserted": rows_inserted,
                "rows_updated": rows_updated,
                "rows_unchanged": rows_unchanged,
                "error_message": error_message,
            },
        )


# ============================================================
# BASE PIPELINE VALIDATION
# ============================================================

def validate_staging(engine):
    table_pairs = [
        ("raw.demographics", "staging.demographics"),
        ("raw.location", "staging.location"),
        ("raw.population", "staging.population"),
        ("raw.services", "staging.services"),
        ("raw.status", "staging.status"),
    ]

    for raw_table, staging_table in table_pairs:
        assert_equal(
            get_table_count(engine, staging_table),
            get_table_count(engine, raw_table),
            f"Row-count mismatch: "
            f"{raw_table} -> {staging_table}",
        )

    assert_zero(
        engine,
        """
        SELECT COUNT(*)
        FROM staging.demographics
        WHERE under_30 IS NULL
           OR senior_citizen IS NULL
           OR married IS NULL
           OR dependents IS NULL;
        """,
        "Unexpected NULL in demographics Boolean columns",
    )

    assert_zero(
        engine,
        """
        SELECT COUNT(*)
        FROM staging.services
        WHERE referred_a_friend IS NULL
           OR phone_service IS NULL
           OR multiple_lines IS NULL
           OR internet_service IS NULL
           OR online_security IS NULL
           OR online_backup IS NULL
           OR device_protection_plan IS NULL
           OR premium_tech_support IS NULL
           OR streaming_tv IS NULL
           OR streaming_movies IS NULL
           OR streaming_music IS NULL
           OR unlimited_data IS NULL
           OR paperless_billing IS NULL;
        """,
        "Unexpected NULL in services Boolean columns",
    )

    assert_zero(
        engine,
        """
        SELECT COUNT(*)
        FROM staging.services
        WHERE
            (internet_service = FALSE
                AND internet_type IS NOT NULL)
            OR
            (internet_service = TRUE
                AND internet_type IS NULL);
        """,
        "Internet service business rule failed",
    )

    assert_zero(
        engine,
        """
        SELECT COUNT(*)
        FROM staging.status
        WHERE
            (churned = TRUE AND churn_value <> 1)
            OR
            (churned = FALSE AND churn_value <> 0);
        """,
        "Churn mapping failed",
    )


def validate_core(engine):
    table_pairs = [
        ("staging.demographics", "core.customer"),
        ("staging.location", "core.location"),
        ("staging.population", "core.population"),
        ("staging.services", "core.services"),
        ("staging.status", "core.customer_status"),
    ]

    for staging_table, core_table in table_pairs:
        assert_equal(
            get_table_count(engine, core_table),
            get_table_count(engine, staging_table),
            f"Row-count mismatch: "
            f"{staging_table} -> {core_table}",
        )

    assert_zero(
        engine,
        """
        SELECT COUNT(*)
        FROM core.location l
        LEFT JOIN core.customer c
            ON l.customer_id = c.customer_id
        WHERE c.customer_id IS NULL;
        """,
        "Orphan customer found in core.location",
    )

    assert_zero(
        engine,
        """
        SELECT COUNT(*)
        FROM core.services s
        LEFT JOIN core.customer c
            ON s.customer_id = c.customer_id
        WHERE c.customer_id IS NULL;
        """,
        "Orphan customer found in core.services",
    )

    assert_zero(
        engine,
        """
        SELECT COUNT(*)
        FROM core.customer_status cs
        LEFT JOIN core.customer c
            ON cs.customer_id = c.customer_id
        WHERE c.customer_id IS NULL;
        """,
        "Orphan customer found in core.customer_status",
    )

    assert_zero(
        engine,
        """
        SELECT COUNT(*)
        FROM core.location l
        LEFT JOIN core.population p
            ON l.zip_code = p.zip_code
        WHERE p.zip_code IS NULL;
        """,
        "Orphan ZIP code found in core.location",
    )


# ============================================================
# BILLING WATERMARK + INCREMENTAL RAW LOAD
# ============================================================

def get_billing_watermark(connection):
    query = text("""
        SELECT last_watermark
        FROM audit.pipeline_watermark
        WHERE pipeline_name = :pipeline_name
          AND source_name = :source_name;
    """)

    watermark = connection.execute(
        query,
        {
            "pipeline_name": PIPELINE_NAME,
            "source_name": BILLING_SOURCE_NAME,
        },
    ).scalar_one_or_none()

    if watermark is None:
        raise RuntimeError(
            "Billing watermark record was not found."
        )

    return pd.Timestamp(watermark)


def update_billing_watermark(
    connection,
    new_watermark,
):
    query = text("""
        UPDATE audit.pipeline_watermark
        SET
            last_watermark = :new_watermark,
            updated_at = CURRENT_TIMESTAMP
        WHERE pipeline_name = :pipeline_name
          AND source_name = :source_name;
    """)

    connection.execute(
        query,
        {
            "new_watermark":
                new_watermark.to_pydatetime(),
            "pipeline_name": PIPELINE_NAME,
            "source_name": BILLING_SOURCE_NAME,
        },
    )
    

# ============================================================
# STRICT BILLING DATE VALIDATION
# ============================================================

def invalid_billing_date_mask(values):

    # Check the exact YYYY-MM-DD text format.
    date_text = values.astype("string")

    correct_format = date_text.str.fullmatch(
        r"\d{4}-\d{2}-\d{2}"
    ).fillna(False)

    # Check that the date actually exists.
    parsed_dates = pd.to_datetime(
        date_text,
        format="%Y-%m-%d",
        errors="coerce"
    )

    # Invalid when either check fails.
    return (~correct_format) | parsed_dates.isna()


# ============================================================
# QUARANTINE INVALID BILLING TIMESTAMPS
# ============================================================

def quarantine_invalid_billing_timestamps(billing, engine, source_file_name=None):

    # A missing column is handled by source validation.
    if "updated_at" not in billing.columns:
        return 0

    invalid_rows = billing.loc[
        invalid_billing_date_mask(billing["updated_at"])
    ].copy()

    if invalid_rows.empty:
        print("No invalid billing timestamps found.")
        return 0

    insert_sql = text("""
        INSERT INTO audit.billing_quarantine (
            bill_id,
            customer_id,
            source_file_name,
            source_row_number,
            raw_record,
            rejection_reason
        )
        SELECT
            :bill_id,
            :customer_id,
            :source_file_name,
            :source_row_number,
            CAST(:raw_record AS JSONB),
            :rejection_reason
        WHERE NOT EXISTS (
            SELECT 1
            FROM audit.billing_quarantine
            WHERE source_file_name = :source_file_name
                AND source_row_number = :source_row_number
                AND raw_record = CAST(:raw_record AS JSONB)
                AND rejection_reason = :rejection_reason
                AND status = 'OPEN'
            );
    """)

    inserted_count = 0

    with engine.begin() as connection:

        for index, row in invalid_rows.iterrows():

            parameters = {
                "bill_id": (
                    None if pd.isna(row.get("bill_id"))
                    else str(row["bill_id"])
                ),
                "customer_id": (
                    None if pd.isna(row.get("customer_id"))
                    else str(row["customer_id"])
                ),
                "source_file_name": source_file_name or BILLING_SOURCE_FILE.name,
                "source_row_number": int(index) + 2,
                "raw_record": row.to_json(),
                "rejection_reason": "Missing or invalid updated_at"
            }

            result = connection.execute(
                insert_sql,
                parameters
            )

            inserted_count += result.rowcount

    print(f"Invalid timestamp records: {len(invalid_rows)}")
    print(f"New records quarantined: {inserted_count}")

    return inserted_count

# ============================================================
# BILLING SOURCE VALIDATION
# ============================================================

def validate_billing_source(billing):

    # 1. Check required columns
    required_columns = [
        "bill_id",
        "customer_id",
        "created_at",
        "updated_at",
    ]

    for column in required_columns:
        if column not in billing.columns:
            raise ValueError(
                f"Missing required column: {column}"
            )

    # 2. Check missing bill IDs and customer IDs
    for column in ["bill_id", "customer_id"]:

        missing = (
            billing[column]
            .fillna("")
            .astype(str)
            .str.strip()
            .eq("")
        )

        if missing.any():
            raise ValueError(
                f"Missing {column}: {missing.sum()} rows"
            )

    

    # 3. Validate source timestamps
    for column in ["created_at", "updated_at"]:

        invalid_mask = invalid_billing_date_mask(
            billing[column]
        )

        if invalid_mask.any():
            raise ValueError(
                f"Missing, invalid, or non-ISO {column} values."
            )

        billing[column] = pd.to_datetime(
            billing[column],
            format="%Y-%m-%d",
            errors="raise"
        )



    # 4. Check timestamp order
    invalid_dates = (
        billing["updated_at"] < billing["created_at"]
    )

    if invalid_dates.any():
        raise ValueError(
            "Some billing records have updated_at "
            "earlier than created_at."
        )

    print("Billing source validation passed.")

    return billing



def load_billing_raw_incremental(engine, source_file = None):
    # Use the normal billing CSV unless another file is provided.
    if source_file is None:
        source_file = BILLING_SOURCE_FILE
    else:
        source_file = Path(source_file)

    if not source_file.exists():
        raise FileNotFoundError(
            f"Billing source file not found: {source_file}"
        )

    billing = pd.read_csv(source_file)

    source_row_count = len(billing)

    # Check that the updated_at column exists.
    if "updated_at" not in billing.columns:
        raise ValueError(
            "Missing required column: updated_at"
        )

    # Identify records with invalid timestamps.
    invalid_mask = invalid_billing_date_mask(
        billing["updated_at"]
    )

    invalid_count = int(invalid_mask.sum())

    # Save invalid records to the quarantine table.
    quarantine_invalid_billing_timestamps(
        billing,
        engine,
        source_file_name=source_file.name
    )

    # Keep only rows with valid updated_at.
    billing = billing.loc[
        ~invalid_mask
    ].copy()

    # Validate the remaining records.
    billing = validate_billing_source(billing)

    print(f"Billing source rows: {source_row_count}")
    print(f"Valid records: {len(billing)}")
    print(f"Quarantined records: {invalid_count}")

    if invalid_count > 0:
        print(
            "WARNING: Some billing records were quarantined "
            "and still require investigation."
        )


    with engine.begin() as connection:
        last_watermark = get_billing_watermark(
            connection
        )

        print(
            f"Billing current watermark: "
            f"{last_watermark}"
        )

        incremental_rows = billing[
            billing["updated_at"] > last_watermark
        ].copy()

        rows_loaded = len(incremental_rows)

        print(
            "Billing new / changed rows found: "
            f"{rows_loaded}"
        )

        if incremental_rows.empty:
            return 0

        incremental_rows[
            "source_file_name"
        ] = source_file.name

        incremental_rows.to_sql(
            name="billing_transactions",
            con=connection,
            schema="raw",
            if_exists="append",
            index=False,
            chunksize=1000,
            method="multi",
        )

        new_watermark = (
            incremental_rows["updated_at"].max()
        )

        update_billing_watermark(
            connection,
            new_watermark,
        )

        print(
            "Billing new watermark: "
            f"{new_watermark}"
        )

        return rows_loaded


# ============================================================
# COUNTED BILLING CORE UPSERT
# ============================================================

def upsert_billing_core_with_metrics(engine):
    """
    Classify STAGING bills against CORE and execute the existing
    22_upsert_billing_core.sql inside the SAME database transaction.

    Returns actual inserted/updated action counts, rather than the
    final total row count of core.billing_transactions.

    This function relies on the query produced in
    31_preview_billing_upsert_actions.sql.
    """

    preview_path = SQL_DIR / "31_preview_billing_upsert_actions.sql"
    upsert_path = SQL_DIR / "22_upsert_billing_core.sql"

    for path in [preview_path, upsert_path]:
        if not path.exists():
            raise FileNotFoundError(f"SQL file not found: {path}")

    preview_sql = preview_path.read_text(encoding="utf-8")
    upsert_sql = upsert_path.read_text(encoding="utf-8")

    # The manual SQL file includes BEGIN/COMMIT. Python controls a
    # single transaction for BOTH classification and UPSERT, so
    # remove the standalone wrappers in memory. The saved SQL
    # file remains unchanged for manual use.
    begin_pattern = r"(?im)^[ \t]*BEGIN[ \t]*;[ \t]*$"
    commit_pattern = r"(?im)^[ \t]*COMMIT[ \t]*;[ \t]*$"

    upsert_sql, begin_count = re.subn(begin_pattern, "", upsert_sql)
    upsert_sql, commit_count = re.subn(commit_pattern, "", upsert_sql)

    if begin_count != 1 or commit_count != 1:
        raise RuntimeError(
            "Expected exactly one standalone BEGIN; and COMMIT; "
            "in 22_upsert_billing_core.sql."
        )

    with engine.begin() as connection:
        # Serialize writers on CORE billing for the duration of
        # classification + UPSERT. Good for this local learning
        # pipeline; high-scale production designs may differ.
        connection.exec_driver_sql(
            "LOCK TABLE core.billing_transactions "
            "IN SHARE ROW EXCLUSIVE MODE"
        )

        result = connection.exec_driver_sql(preview_sql)
        counts = dict(result.mappings().one())

        inserted = int(counts["rows_to_insert"])
        updated = int(counts["rows_to_update"])
        unchanged = int(counts["rows_unchanged"])
        invalid = int(counts["invalid_rows"])
        total = int(counts["staging_rows"])

        if invalid:
            raise RuntimeError(
                f"Billing STAGING contains {invalid} invalid "
                "bill_id / updated_at values."
            )

        if inserted + updated + unchanged != total:
            raise RuntimeError(
                "Billing action categories do not add up "
                "to STAGING row count."
            )

        # One INSERT...ON CONFLICT SQL statement. rowcount from
        # PostgreSQL counts actual inserted + updated rows.
        statement_result = connection.exec_driver_sql(upsert_sql)
        actual_changed = statement_result.rowcount

        if actual_changed != inserted + updated:
            raise RuntimeError(
                "UPSERT affected a different number of rows "
                f"than expected: expected {inserted + updated}, "
                f"got {actual_changed}. Transaction rolled back."
            )

    # We only return metrics AFTER the UPSERT transaction commits.
    return {
        "rows_processed": actual_changed,
        "rows_inserted": inserted,
        "rows_updated": updated,
        "rows_unchanged": unchanged,
    }


# ============================================================
# BILLING STAGING VALIDATION (BEFORE CORE UPSERT)
# ============================================================

def validate_billing_staging(engine):
    # Running the manual SQL file only prints results. These
    # Python checks must RAISE errors to stop the orchestrator.
    raw_unique_bills = get_scalar(
        engine,
        "SELECT COUNT(DISTINCT bill_id) FROM raw.billing_transactions",
    )
    staging_rows = get_table_count(engine, "staging.billing_transactions")

    assert_equal(
        staging_rows,
        raw_unique_bills,
        "Billing STAGING count differs from unique RAW bill count",
    )

    assert_zero(
        engine,
        """
        SELECT COUNT(*)
        FROM (
            SELECT bill_id
            FROM staging.billing_transactions
            GROUP BY bill_id
            HAVING COUNT(*) > 1
        ) duplicate_bills;
        """,
        "Duplicate bill IDs found in Billing STAGING",
    )

    assert_zero(
        engine,
        """
        SELECT COUNT(*)
        FROM staging.billing_transactions s
        WHERE EXISTS (
            SELECT 1
            FROM raw.billing_transactions r
            WHERE r.bill_id = s.bill_id
              AND r.updated_at > s.updated_at
        );
        """,
        "Outdated bill version found in Billing STAGING",
    )

    assert_zero(
        engine,
        """
        SELECT COUNT(*)
        FROM (
            SELECT DISTINCT bill_id
            FROM raw.billing_transactions
            WHERE bill_id IS NOT NULL
        ) r
        LEFT JOIN staging.billing_transactions s
            ON r.bill_id = s.bill_id
        WHERE s.bill_id IS NULL;
        """,
        "RAW bill IDs missing from Billing STAGING",
    )

    assert_zero(
        engine,
        """
        SELECT COUNT(*)
        FROM staging.billing_transactions
        WHERE bill_id IS NULL
           OR updated_at IS NULL;
        """,
        "Missing billing IDs or updated_at values in STAGING",
    )


# ============================================================
# BILLING VALIDATION
# ============================================================

def validate_billing(engine):
    raw_unique_bills = get_scalar(
        engine,
        """
        SELECT COUNT(DISTINCT bill_id)
        FROM raw.billing_transactions;
        """,
    )

    staging_rows = get_table_count(
        engine,
        "staging.billing_transactions",
    )

    core_rows = get_table_count(
        engine,
        "core.billing_transactions",
    )

    assert_equal(
        staging_rows,
        raw_unique_bills,
        "Billing STAGING row count does not "
        "match distinct RAW bill count",
    )

    assert_equal(
        core_rows,
        staging_rows,
        "Billing CORE row count does not "
        "match STAGING row count",
    )

    assert_zero(
        engine,
        """
        SELECT COUNT(*)
        FROM (
            SELECT bill_id
            FROM staging.billing_transactions
            GROUP BY bill_id
            HAVING COUNT(*) > 1
        ) duplicates;
        """,
        "Duplicate bill_id found in billing STAGING",
    )

    assert_zero(
        engine,
        """
        SELECT COUNT(*)
        FROM staging.billing_transactions s
        WHERE EXISTS (
            SELECT 1
            FROM raw.billing_transactions r
            WHERE r.bill_id = s.bill_id
              AND r.updated_at > s.updated_at
        );
        """,
        "Outdated bill version found in STAGING",
    )

    assert_zero(
        engine,
        """
        SELECT COUNT(*)
        FROM staging.billing_transactions s
        LEFT JOIN core.billing_transactions c
            ON s.bill_id = c.bill_id
        WHERE c.bill_id IS NULL;
        """,
        "Billing bill missing from CORE",
    )

    assert_zero(
        engine,
        """
        SELECT COUNT(*)
        FROM core.billing_transactions c
        JOIN staging.billing_transactions s
            ON c.bill_id = s.bill_id
        WHERE c.updated_at < s.updated_at;
        """,
        "Outdated bill version found in CORE",
    )

    assert_zero(
        engine,
        """
        SELECT COUNT(*)
        FROM core.billing_transactions b
        LEFT JOIN core.customer c
            ON b.customer_id = c.customer_id
        WHERE c.customer_id IS NULL;
        """,
        "Orphan billing customer found in CORE",
    )

    assert_zero(
        engine,
        """
        SELECT COUNT(*)
        FROM core.billing_transactions
        WHERE payment_status NOT IN (
            'Paid',
            'Pending',
            'Failed'
        );
        """,
        "Invalid billing payment status found",
    )

    assert_zero(
        engine,
        """
        SELECT COUNT(*)
        FROM core.billing_transactions
        WHERE base_monthly_charge < 0
           OR long_distance_charge < 0
           OR extra_data_charge < 0
           OR discount_amount < 0
           OR total_amount < 0;
        """,
        "Negative billing amount found",
    )

    assert_zero(
        engine,
        """
        SELECT COUNT(*)
        FROM core.billing_transactions
        WHERE updated_at < created_at;
        """,
        "Invalid billing source timestamp found",
    )


# ============================================================
# MART VALIDATION
# ============================================================

def validate_mart(engine):
    assert_equal(
        get_table_count(
            engine,
            "mart.customer_360",
        ),
        get_table_count(
            engine,
            "core.customer",
        ),
        "mart.customer_360 row count does not "
        "match core.customer",
    )

    assert_zero(
        engine,
        """
        SELECT COUNT(*)
        FROM (
            SELECT customer_id
            FROM mart.customer_360
            GROUP BY customer_id
            HAVING COUNT(*) > 1
        ) duplicates;
        """,
        "Duplicate customers found in "
        "mart.customer_360",
    )

    assert_zero(
        engine,
        """
        SELECT COUNT(*)
        FROM mart.customer_360
        WHERE city IS NULL
           OR contract IS NULL
           OR customer_status IS NULL;
        """,
        "Unexpected missing joined data in "
        "mart.customer_360",
    )


# ============================================================
# ADDITIONAL MART VALIDATION
# ============================================================

def validate_billing_summary_mart(engine):
    # The mart contains only customers with at least one bill.
    unique_billed_customers = get_scalar(
        engine,
        "SELECT COUNT(DISTINCT customer_id) "
        "FROM core.billing_transactions"
    )
    assert_equal(
        get_table_count(engine, "mart.customer_billing_summary"),
        unique_billed_customers,
        "Billing summary customer count mismatch",
    )

    assert_zero(
        engine,
        """
        SELECT COUNT(*)
        FROM (
            SELECT customer_id
            FROM mart.customer_billing_summary
            GROUP BY customer_id
            HAVING COUNT(*) > 1
        ) d;
        """,
        "Duplicate customers in billing summary",
    )

    assert_zero(
        engine,
        """
        SELECT COUNT(*)
        FROM mart.customer_billing_summary
        WHERE paid_bill_count + pending_bill_count
              + failed_bill_count <> number_of_bills;
        """,
        "Billing summary payment counts do not reconcile",
    )

    core_count = get_table_count(engine, "core.billing_transactions")
    mart_count = get_scalar(
        engine,
        "SELECT COALESCE(SUM(number_of_bills), 0) "
        "FROM mart.customer_billing_summary"
    )
    assert_equal(mart_count, core_count, "Billing summary bill count mismatch")

    assert_zero(
        engine,
        """
        SELECT CASE WHEN
            (SELECT SUM(total_amount) FROM core.billing_transactions)
            IS DISTINCT FROM
            (SELECT SUM(total_billed_amount)
             FROM mart.customer_billing_summary)
        THEN 1 ELSE 0 END;
        """,
        "Billing summary total amount mismatch",
    )


def validate_enriched_customer_360_mart(engine):
    assert_equal(
        get_table_count(engine, "mart.customer_360_enriched"),
        get_table_count(engine, "core.customer"),
        "Enriched customer count mismatch",
    )

    assert_zero(
        engine,
        """
        SELECT COUNT(*)
        FROM (
            SELECT customer_id
            FROM mart.customer_360_enriched
            GROUP BY customer_id
            HAVING COUNT(*) > 1
        ) d;
        """,
        "Duplicate customers in enriched mart",
    )

    assert_zero(
        engine,
        """
        SELECT COUNT(*)
        FROM core.customer c
        LEFT JOIN mart.customer_360_enriched e
            ON c.customer_id = e.customer_id
        WHERE e.customer_id IS NULL;
        """,
        "Missing CORE customers in enriched mart",
    )

    assert_zero(
        engine,
        """
        SELECT COUNT(*)
        FROM mart.customer_360_enriched
        WHERE paid_bill_count + pending_bill_count
              + failed_bill_count <> number_of_bills;
        """,
        "Enriched mart payment counts do not reconcile",
    )

    assert_zero(
        engine,
        """
        SELECT COUNT(*)
        FROM mart.customer_360_enriched e
        JOIN mart.customer_billing_summary b
            ON e.customer_id = b.customer_id
        WHERE e.number_of_bills IS DISTINCT FROM b.number_of_bills
           OR e.total_billed_amount IS DISTINCT FROM b.total_billed_amount
           OR e.average_bill_amount IS DISTINCT FROM b.average_bill_amount
           OR e.total_discount_amount IS DISTINCT FROM b.total_discount_amount
           OR e.billing_long_distance_charge
                IS DISTINCT FROM b.total_long_distance_charge
           OR e.billing_extra_data_charge
                IS DISTINCT FROM b.total_extra_data_charge
           OR e.paid_bill_count IS DISTINCT FROM b.paid_bill_count
           OR e.pending_bill_count IS DISTINCT FROM b.pending_bill_count
           OR e.failed_bill_count IS DISTINCT FROM b.failed_bill_count
           OR e.first_billing_date IS DISTINCT FROM b.first_billing_date
           OR e.latest_billing_date IS DISTINCT FROM b.latest_billing_date;
        """,
        "Enriched mart billing metrics differ from billing summary",
    )


# ============================================================
# PIPELINE STEP WRAPPER
# ============================================================

def run_step(
    engine,
    run_id,
    step_name,
    action,
    rows_processed_function=None,
):
    print(f"\n{step_name}...")

    step_id = start_pipeline_step(
        engine,
        run_id,
        step_name,
    )

    try:
        result = action()

        rows_processed = None

        if rows_processed_function is not None:
            rows_processed = rows_processed_function(
                result
            )

        # Only the counted billing UPSERT returns this metrics
        # dictionary; other steps keep their existing behavior.
        metrics = result if isinstance(result, dict) else {}

        finish_pipeline_step(
            engine,
            step_id,
            "SUCCESS",
            rows_processed=rows_processed,
            rows_inserted=metrics.get("rows_inserted"),
            rows_updated=metrics.get("rows_updated"),
            rows_unchanged=metrics.get("rows_unchanged"),
        )

        if metrics:
            print(
                f"Inserted: {metrics['rows_inserted']} | "
                f"Updated: {metrics['rows_updated']} | "
                f"Unchanged: {metrics['rows_unchanged']}"
            )

        print("SUCCESS")

        return result

    except Exception as error:
        finish_pipeline_step(
            engine,
            step_id,
            "FAILED",
            error_message=str(error),
        )

        print("FAILED")
        raise


# ============================================================
# MAIN PIPELINE
# ============================================================

def main():
    engine = get_engine()

    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    print("Database connection successful.")

    run_id = start_pipeline_run(engine)

    print("\n" + "=" * 60)
    print("TELCO CUSTOMER 360 PIPELINE")
    print(f"Run ID: {run_id}")
    print("=" * 60)

    try:
        run_step(
            engine,
            run_id,
            "1. Transform Base STAGING",
            lambda: execute_sql_file(
                engine,
                "06_transform_staging.sql",
            ),
            lambda _: sum(
                get_table_count(engine, table)
                for table in [
                    "staging.demographics",
                    "staging.location",
                    "staging.population",
                    "staging.services",
                    "staging.status",
                ]
            ),
        )

        run_step(
            engine,
            run_id,
            "2. Validate Base STAGING",
            lambda: validate_staging(engine),
        )

        run_step(
            engine,
            run_id,
            "3. UPSERT Base CORE",
            lambda: execute_sql_file(
                engine,
                "25_upsert_base_core.sql",
            ),
            lambda _: sum(
                get_table_count(engine, table)
                for table in [
                    "core.customer",
                    "core.location",
                    "core.population",
                    "core.services",
                    "core.customer_status",
                ]
            ),
        )

        run_step(
            engine,
            run_id,
            "4. Validate Base CORE",
            lambda: validate_core(engine),
        )

        run_step(
            engine,
            run_id,
            "5. Incremental Billing RAW Load",
            lambda: load_billing_raw_incremental(
                engine
            ),
            lambda rows_loaded: rows_loaded,
        )

        run_step(
            engine,
            run_id,
            "6. Transform Billing STAGING",
            lambda: execute_sql_file(
                engine,
                "20_transform_billing_staging.sql",
            ),
            lambda _: get_table_count(
                engine,
                "staging.billing_transactions",
            ),
        )

        run_step(
            engine,
            run_id,
            "7. Validate Billing STAGING",
            lambda: validate_billing_staging(engine),
        )

        run_step(
            engine,
            run_id,
            "8. UPSERT Billing CORE",
            lambda: upsert_billing_core_with_metrics(engine),
            lambda metrics: metrics["rows_processed"],
        )

        run_step(
            engine,
            run_id,
            "9. Validate Billing Pipeline",
            lambda: validate_billing(engine),
        )

        run_step(
            engine,
            run_id,
            "10. Build Customer 360 MART",
            lambda: execute_sql_file(
                engine,
                "12_create_customer_360_mart.sql",
            ),
            lambda _: get_table_count(
                engine,
                "mart.customer_360",
            ),
        )

        run_step(
            engine,
            run_id,
            "11. Validate Customer 360 MART",
            lambda: validate_mart(engine),
        )

        run_step(
            engine,
            run_id,
            "12. Build Billing Summary MART",
            lambda: execute_sql_file(
                engine, "26_create_customer_billing_mart.sql"
            ),
            lambda _: get_table_count(
                engine, "mart.customer_billing_summary"
            ),
        )

        run_step(
            engine,
            run_id,
            "13. Validate Billing Summary MART",
            lambda: validate_billing_summary_mart(engine),
        )

        run_step(
            engine,
            run_id,
            "14. Build Enriched Customer 360 MART",
            lambda: execute_sql_file(
                engine, "28_create_enriched_customer_360_mart.sql"
            ),
            lambda _: get_table_count(
                engine, "mart.customer_360_enriched"
            ),
        )

        run_step(
            engine,
            run_id,
            "15. Validate Enriched Customer 360 MART",
            lambda: validate_enriched_customer_360_mart(engine),
        )

        finish_pipeline_run(
            engine,
            run_id,
            "SUCCESS",
        )

        print("\n" + "=" * 60)
        print("PIPELINE COMPLETED SUCCESSFULLY")
        print(f"Run ID: {run_id}")
        print("=" * 60)

    except Exception as error:
        finish_pipeline_run(
            engine,
            run_id,
            "FAILED",
            error_message=str(error),
        )

        print("\n" + "=" * 60)
        print("PIPELINE FAILED")
        print(f"Run ID: {run_id}")
        print(f"Error: {error}")
        print("=" * 60)

        raise


if __name__ == "__main__":
    main()
