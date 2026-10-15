
import pandas as pd
import runpy
from pathlib import Path
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[1]

CORRECTED_FILE = (
    PROJECT_ROOT
    / "data"
    / "test"
    / "billing_recovery_corrected.csv"
)

# Load reusable functions from our existing pipeline.
pipeline = runpy.run_path(
    str(PROJECT_ROOT / "src" / "15_run_pipeline.py")
)

get_engine = pipeline["get_engine"]
get_billing_watermark = pipeline["get_billing_watermark"]
validate_billing_source = pipeline["validate_billing_source"]

# 1. Read and validate the corrected record.
billing = pd.read_csv(CORRECTED_FILE)

if len(billing) != 1:
    raise ValueError("Expected exactly one corrected bill.")

billing = validate_billing_source(billing)

bill = billing.iloc[0]

if bill["bill_id"] != "BTEST-RECOVERY-001":
    raise ValueError("Unexpected bill ID.")

# 2. Connect to PostgreSQL.
engine = get_engine()

with engine.begin() as connection:

    # 3. Verify the corresponding quarantine case.
    quarantine = connection.execute(
        text("""
            SELECT
                quarantine_id,
                bill_id,
                customer_id,
                source_file_name,
                status
            FROM audit.billing_quarantine
            WHERE quarantine_id = 4
            FOR UPDATE
        """)
    ).mappings().one_or_none()

    if (
        quarantine is None
        or quarantine["bill_id"] != bill["bill_id"]
        or quarantine["customer_id"] != bill["customer_id"]
        or quarantine["source_file_name"]
            != "billing_recovery_invalid.csv"
        or quarantine["status"] != "OPEN"
    ):
        raise RuntimeError(
            "Expected OPEN quarantine record not found."
        )

    # 4. Verify this is an older-than-watermark recovery.
    watermark = get_billing_watermark(connection)

    print("Current watermark:", watermark)
    print("Corrected updated_at:", bill["updated_at"])

    if bill["updated_at"] >= watermark:
        raise RuntimeError(
            "This test expects updated_at older than watermark."
        )

    # 5. Lock RAW while checking for duplicates and inserting.
    connection.exec_driver_sql(
        "LOCK TABLE raw.billing_transactions "
        "IN SHARE ROW EXCLUSIVE MODE"
    )

    raw_count = connection.execute(
        text("""
            SELECT COUNT(*)
            FROM raw.billing_transactions
            WHERE bill_id = :bill_id
        """),
        {"bill_id": bill["bill_id"]}
    ).scalar_one()

    core_count = connection.execute(
        text("""
            SELECT COUNT(*)
            FROM core.billing_transactions
            WHERE bill_id = :bill_id
        """),
        {"bill_id": bill["bill_id"]}
    ).scalar_one()

    if raw_count != 0 or core_count != 0:
        raise RuntimeError(
            "Test bill already exists in RAW or CORE."
        )

    # 6. Confirm the customer exists.
    customer_count = connection.execute(
        text("""
            SELECT COUNT(*)
            FROM core.customer
            WHERE customer_id = :customer_id
        """),
        {"customer_id": bill["customer_id"]}
    ).scalar_one()

    if customer_count != 1:
        raise RuntimeError(
            "Customer does not exist in CORE."
        )

    # 7. Replay the corrected record directly into RAW.
    billing["source_file_name"] = CORRECTED_FILE.name

    billing.to_sql(
        name="billing_transactions",
        con=connection,
        schema="raw",
        if_exists="append",
        index=False
    )

    print("Corrected bill inserted into RAW.")
    print("Bill ID:", bill["bill_id"])

print("Recovery RAW transaction completed successfully.")
print("Watermark was not changed.")
print("Quarantine remains OPEN until CORE verification.")
