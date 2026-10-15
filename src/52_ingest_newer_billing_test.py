
import runpy
import pandas as pd

from pathlib import Path
from sqlalchemy import text


PROJECT_ROOT = Path(__file__).resolve().parents[1]

CORRECTED_FILE = (
    PROJECT_ROOT
    / "data"
    / "test"
    / "billing_newer_corrected.csv"
)

BILL_ID = "B202601-0420-BWTPW"


# 1. Load existing pipeline functions.
pipeline = runpy.run_path(
    str(PROJECT_ROOT / "src" / "15_run_pipeline.py")
)

get_engine = pipeline["get_engine"]
get_billing_watermark = pipeline["get_billing_watermark"]

load_billing_raw_incremental = pipeline[
    "load_billing_raw_incremental"
]


# 2. Verify our test file.
billing = pd.read_csv(CORRECTED_FILE)

if len(billing) != 1:
    raise ValueError("Expected exactly one corrected record.")

if billing.iloc[0]["bill_id"] != BILL_ID:
    raise ValueError("Unexpected bill ID.")

if billing.iloc[0]["payment_status"] != "Paid":
    raise ValueError("Expected Paid status.")


# 3. Connect to PostgreSQL.
engine = get_engine()


# 4. Check the database before ingestion.
with engine.connect() as connection:

    watermark = get_billing_watermark(connection)

    if watermark != pd.Timestamp("2026-06-07"):
        raise RuntimeError("Unexpected current watermark.")

    quarantine_status = connection.execute(
        text("""
            SELECT status
            FROM audit.billing_quarantine
            WHERE quarantine_id = 6
              AND bill_id = :bill_id
        """),
        {"bill_id": BILL_ID}
    ).scalar_one_or_none()

    if quarantine_status != "OPEN":
        raise RuntimeError("Expected OPEN quarantine case.")

    raw_versions = connection.execute(
        text("""
            SELECT payment_status, updated_at
            FROM raw.billing_transactions
            WHERE bill_id = :bill_id
        """),
        {"bill_id": BILL_ID}
    ).mappings().all()

    if (
        len(raw_versions) != 1
        or raw_versions[0]["payment_status"] != "Pending"
        or pd.Timestamp(raw_versions[0]["updated_at"])
            != pd.Timestamp("2026-01-01")
    ):
        raise RuntimeError("Unexpected RAW billing history.")


# 5. Run the normal incremental loader using our test CSV.
rows_loaded = load_billing_raw_incremental(
    engine,
    source_file=CORRECTED_FILE
)

if rows_loaded != 1:
    raise RuntimeError("Expected exactly one inserted RAW row.")

print("Recovery ingestion completed.")
print("Bill ID:", BILL_ID)
print("Rows loaded:", rows_loaded)
print("CORE has not been refreshed yet.")
