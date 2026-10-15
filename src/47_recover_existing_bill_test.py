
import pandas as pd
import runpy

from decimal import Decimal
from pathlib import Path
from sqlalchemy import text


PROJECT_ROOT = Path(__file__).resolve().parents[1]

CORRECTED_FILE = (
    PROJECT_ROOT
    / "data"
    / "test"
    / "billing_existing_corrected.csv"
)

BILL_ID = "B202601-0215-BQKGS"
QUARANTINE_ID = 5


# ============================================================
# 1. LOAD EXISTING PIPELINE FUNCTIONS
# ============================================================

pipeline = runpy.run_path(
    str(PROJECT_ROOT / "src" / "15_run_pipeline.py")
)

get_engine = pipeline["get_engine"]
get_billing_watermark = pipeline["get_billing_watermark"]
validate_billing_source = pipeline["validate_billing_source"]


# ============================================================
# 2. CHECK WHETHER TWO BILL VERSIONS MATCH
# ============================================================

def versions_match(existing, corrected):

    text_columns = [
        "bill_id",
        "customer_id",
        "payment_status",
        "payment_method",
    ]

    amount_columns = [
        "base_monthly_charge",
        "long_distance_charge",
        "extra_data_charge",
        "discount_amount",
        "total_amount",
    ]

    for column in text_columns:
        if existing[column] != corrected[column]:
            return False

    for column in amount_columns:
        if Decimal(str(existing[column])) != Decimal(str(corrected[column])):
            return False

    if str(existing["billing_date"])[:10] != str(corrected["billing_date"])[:10]:
        return False

    for column in ["created_at", "updated_at"]:
        if pd.Timestamp(existing[column]) != pd.Timestamp(corrected[column]):
            return False

    return True


# ============================================================
# 3. READ AND VALIDATE CORRECTED CSV
# ============================================================

billing = pd.read_csv(CORRECTED_FILE)

if len(billing) != 1:
    raise ValueError("Expected exactly one corrected bill.")

billing = validate_billing_source(billing)

bill = billing.iloc[0]

if bill["bill_id"] != BILL_ID:
    raise ValueError("Unexpected bill ID.")

if bill["payment_status"] != "Paid":
    raise ValueError("Corrected payment status must be Paid.")

if bill["created_at"] != pd.Timestamp("2026-01-01"):
    raise ValueError("Unexpected created_at.")

if bill["updated_at"] != pd.Timestamp("2026-03-02"):
    raise ValueError("Unexpected corrected updated_at.")


# ============================================================
# 4. CONNECT TO POSTGRESQL
# ============================================================

engine = get_engine()

action = None

with engine.begin() as connection:

    # ========================================================
    # 5. VERIFY THE OPEN QUARANTINE CASE
    # ========================================================

    quarantine = connection.execute(
        text("""
            SELECT
                quarantine_id,
                bill_id,
                customer_id,
                source_file_name,
                status,
                raw_record ->> 'payment_status'
                    AS rejected_payment_status

            FROM audit.billing_quarantine

            WHERE quarantine_id = :quarantine_id

            FOR UPDATE
        """),
        {"quarantine_id": QUARANTINE_ID}
    ).mappings().one_or_none()

    if (
        quarantine is None
        or quarantine["bill_id"] != BILL_ID
        or quarantine["customer_id"] != bill["customer_id"]
        or quarantine["source_file_name"] != "billing_existing_invalid.csv"
        or quarantine["rejected_payment_status"] != "Paid"
        or quarantine["status"] != "OPEN"
    ):
        raise RuntimeError(
            "Expected OPEN quarantine case not found."
        )

    # ========================================================
    # 6. CHECK THE WATERMARK
    # ========================================================

    watermark = get_billing_watermark(connection)

    print("Current watermark:", watermark)
    print("Corrected updated_at:", bill["updated_at"])

    if bill["updated_at"] >= watermark:
        raise RuntimeError(
            "This test expects a date older than the watermark."
        )

    # ========================================================
    # 7. LOCK AND CHECK RAW VERSIONS
    # ========================================================

    connection.exec_driver_sql(
        "LOCK TABLE raw.billing_transactions "
        "IN SHARE ROW EXCLUSIVE MODE"
    )

    raw_versions = connection.execute(
        text("""
            SELECT *
            FROM raw.billing_transactions
            WHERE bill_id = :bill_id
            ORDER BY updated_at
        """),
        {"bill_id": BILL_ID}
    ).mappings().all()

    if not raw_versions:
        raise RuntimeError(
            "The original RAW bill was not found."
        )

    # Check whether a newer version already exists.
    if any(
        pd.Timestamp(row["updated_at"]) > bill["updated_at"]
        for row in raw_versions
    ):
        raise RuntimeError(
            "RAW already contains a newer bill version."
        )

    # ========================================================
    # 8. PREVENT DUPLICATE RECOVERY
    # ========================================================

    matching_timestamp = [
        row for row in raw_versions
        if pd.Timestamp(row["updated_at"]) == bill["updated_at"]
    ]

    if matching_timestamp:

        if (
            len(matching_timestamp) != 1
            or not versions_match(matching_timestamp[0], bill)
        ):
            raise RuntimeError(
                "A conflicting RAW version has the same timestamp."
            )

        action = "SKIPPED"

    else:

        # Confirm the expected original Pending version.
        if (
            len(raw_versions) != 1
            or raw_versions[0]["payment_status"] != "Pending"
            or pd.Timestamp(raw_versions[0]["updated_at"])
                != pd.Timestamp("2026-01-01")
        ):
            raise RuntimeError(
                "Unexpected existing RAW history."
            )

        # ================================================
        # 9. INSERT CORRECTED PAID VERSION INTO RAW
        # ================================================

        billing["source_file_name"] = CORRECTED_FILE.name

        billing.to_sql(
            name="billing_transactions",
            con=connection,
            schema="raw",
            if_exists="append",
            index=False
        )

        action = "INSERTED"


print("Recovery action:", action)
print("Bill ID:", BILL_ID)
print("Watermark was not modified.")
print("Quarantine remains OPEN until CORE verification.")
