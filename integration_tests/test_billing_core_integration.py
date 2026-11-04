r"""Integration test for Telco billing CORE UPSERT against isolated Docker PostgreSQL.

Place this file at integration_tests/test_billing_core_integration.py.
Run from project root:
    .venv\Scripts\python.exe -m pytest integration_tests -v

This pytest test uses real PostgreSQL, the project's actual UPSERT SQL,
and one outer transaction that is rolled back. Seven SQL checks run
inside one pytest test function.
"""
from pathlib import Path
import re
import subprocess

PROJECT_ROOT = Path(__file__).resolve().parents[1]
UPSERT_FILE = PROJECT_ROOT / "sql" / "22_upsert_billing_core.sql"
COMPOSE_FILE = PROJECT_ROOT / "compose.integration.yaml"

CUSTOMER_ID = "ITEST_CORE_C001"
BILL_ID = "ITEST_CORE_B001"

STAGING_COLUMNS = """
    bill_id, customer_id, billing_date,
    base_monthly_charge, long_distance_charge, extra_data_charge,
    discount_amount, total_amount, payment_method, payment_status,
    created_at, updated_at, source_file_name, ingested_at, transformed_at
"""


def load_upsert_without_transaction_wrappers():
    sql = UPSERT_FILE.read_text(encoding="utf-8")
    sql, begins = re.subn(r"(?im)^[ \t]*BEGIN[ \t]*;[ \t]*$", "", sql)
    sql, commits = re.subn(r"(?im)^[ \t]*COMMIT[ \t]*;[ \t]*$", "", sql)
    if (begins, commits) != (1, 1):
        raise ValueError(
            "Expected exactly one standalone BEGIN; and COMMIT; in "
            "sql/22_upsert_billing_core.sql; refusing to run to protect rollback."
        )
    return sql


def stage_bill(status, updated_at):
    return f"""
TRUNCATE TABLE staging.billing_transactions;
INSERT INTO staging.billing_transactions ({STAGING_COLUMNS})
VALUES (
    '{BILL_ID}', '{CUSTOMER_ID}', DATE '2026-06-01',
    100.00, 10.00, 5.00, 5.00, 110.00, 'Credit Card', '{status}',
    TIMESTAMP '2026-06-01 08:00:00', TIMESTAMP '{updated_at}',
    'billing_core_integration_test.csv', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
);
"""


def assert_bill(label, status, updated_at):
    return f"""
DO $test$
BEGIN
    IF (SELECT COUNT(*) FROM core.billing_transactions
        WHERE bill_id = '{BILL_ID}') <> 1 THEN
        RAISE EXCEPTION 'FAIL {label}: expected exactly one CORE bill';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM core.billing_transactions
        WHERE bill_id = '{BILL_ID}'
          AND customer_id = '{CUSTOMER_ID}'
          AND payment_status = '{status}'
          AND updated_at = TIMESTAMP '{updated_at}'
    ) THEN
        RAISE EXCEPTION 'FAIL {label}: CORE bill has incorrect status/timestamp';
    END IF;
    RAISE NOTICE 'PASS {label}';
END
$test$;
"""


def constraint_checks():
    return f"""
DO $test$
BEGIN
    -- Inherit every mandatory value from the known-valid CORE bill,
    -- but reference a customer that does not exist.
    BEGIN
        INSERT INTO core.billing_transactions ({STAGING_COLUMNS})
        SELECT 'ITEST_BAD_FK', 'ITEST_BAD_CUST', billing_date,
               base_monthly_charge, long_distance_charge,
               extra_data_charge, discount_amount, total_amount,
               payment_method, payment_status, created_at, updated_at,
               source_file_name, ingested_at, transformed_at
        FROM core.billing_transactions WHERE bill_id = '{BILL_ID}';
        RAISE EXCEPTION 'FAIL: nonexistent customer was accepted';
    EXCEPTION WHEN foreign_key_violation THEN
        RAISE NOTICE 'PASS foreign-key enforcement';
    END;

    -- Keep everything valid except total_amount.
    BEGIN
        INSERT INTO core.billing_transactions ({STAGING_COLUMNS})
        SELECT 'ITEST_BAD_AMOUNT', customer_id, billing_date,
               base_monthly_charge, long_distance_charge,
               extra_data_charge, discount_amount, -1.00,
               payment_method, payment_status, created_at, updated_at,
               source_file_name, ingested_at, transformed_at
        FROM core.billing_transactions WHERE bill_id = '{BILL_ID}';
        RAISE EXCEPTION 'FAIL: negative total_amount was accepted';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'PASS nonnegative total_amount constraint';
    END;

    -- Keep everything valid except payment_status.
    BEGIN
        INSERT INTO core.billing_transactions ({STAGING_COLUMNS})
        SELECT 'ITEST_BAD_STATUS', customer_id, billing_date,
               base_monthly_charge, long_distance_charge,
               extra_data_charge, discount_amount,
               total_amount, payment_method, 'Unknown',
               created_at, updated_at, source_file_name,
               ingested_at, transformed_at
        FROM core.billing_transactions WHERE bill_id = '{BILL_ID}';
        RAISE EXCEPTION 'FAIL: unknown payment status was accepted';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'PASS allowed payment_status constraint';
    END;
END
$test$;
"""


def main():
    if not UPSERT_FILE.is_file() or not COMPOSE_FILE.is_file():
        raise FileNotFoundError(
            "Required files not found. Save this script in "
            "integration_tests/ alongside sql/ and compose.integration.yaml."
        )
    upsert = load_upsert_without_transaction_wrappers()
    sql = f"""
\\set ON_ERROR_STOP on
BEGIN;

-- Create a minimal STAGING fixture if absent in this isolated test DB.
-- The outer ROLLBACK will remove this table if newly created and restore
-- existing STAGING data after the TRUNCATE operations below.
CREATE SCHEMA IF NOT EXISTS staging;
CREATE TABLE IF NOT EXISTS staging.billing_transactions (
    bill_id VARCHAR(30),
    customer_id VARCHAR(20),
    billing_date DATE,
    base_monthly_charge NUMERIC(12,2),
    long_distance_charge NUMERIC(12,2),
    extra_data_charge NUMERIC(12,2),
    discount_amount NUMERIC(12,2),
    total_amount NUMERIC(12,2),
    payment_method VARCHAR(50),
    payment_status VARCHAR(20),
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    source_file_name VARCHAR(255),
    ingested_at TIMESTAMP,
    transformed_at TIMESTAMP
);

-- Use your real core.customer definition, including all NOT NULL fields.
INSERT INTO core.customer (
    customer_id, gender, age, under_30, senior_citizen,
    married, dependents, number_of_dependents,
    source_file_name, ingested_at, transformed_at
) VALUES (
    '{CUSTOMER_ID}', 'Female', 30, FALSE, FALSE,
    FALSE, FALSE, 0,
    'billing_core_integration_test.csv', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
);

-- Keep STAGING isolated from previous fixtures; rollback restores its contents.
{stage_bill('Pending', '2026-06-02 08:00:00')}
{upsert}
{assert_bill('new-bill insert', 'Pending', '2026-06-02 08:00:00')}

{stage_bill('Paid', '2026-06-05 08:00:00')}
{upsert}
{assert_bill('newer-version update', 'Paid', '2026-06-05 08:00:00')}

{stage_bill('Pending', '2026-06-03 08:00:00')}
{upsert}
{assert_bill('older-version ignored', 'Paid', '2026-06-05 08:00:00')}

-- Re-running the same older source row must also leave CORE unchanged.
{upsert}
{assert_bill('repeat UPSERT no duplicates', 'Paid', '2026-06-05 08:00:00')}

{constraint_checks()}

-- No test fixtures are committed, including customer, CORE, and STAGING.
ROLLBACK;
\\echo PASS: PostgreSQL transaction rolled back; test fixtures not persisted.
"""
    command = [
        "docker", "compose", "-p", "telco-integration-test",
        "-f", str(COMPOSE_FILE), "exec", "-T", "postgres_test",
        "psql", "-X", "-U", "telco_test_user", "-d", "telco_test",
        "-v", "ON_ERROR_STOP=1", "-f", "-",
    ]
    print("Running billing CORE integration tests against telco_test...")
    try:
        result = subprocess.run(
            command, input=sql, text=True, encoding="utf-8",
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            cwd=PROJECT_ROOT, check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("Docker command not found; check Docker Desktop / PATH.") from exc
    print(result.stdout)
    assert result.returncode == 0, (
        f"psql exited with code {result.returncode}. "
        "The transaction is rolled back on disconnect. "
        f"Full output:\n{result.stdout}"
    )
    print("ALL CORE INTEGRATION TESTS PASSED. Test DB fixtures rolled back.")


def test_billing_core_upsert_against_postgres():
    """Pytest discovers this function and runs all CORE SQL assertions."""
    main()


if __name__ == "__main__":
    main()
