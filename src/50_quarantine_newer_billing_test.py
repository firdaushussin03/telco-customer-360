
import pandas as pd
import runpy
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

TEST_FILE = (
    PROJECT_ROOT
    / "data"
    / "test"
    / "billing_newer_invalid.csv"
)

BILL_ID = "B202601-0420-BWTPW"


# ============================================================
# 1. LOAD EXISTING PIPELINE FUNCTIONS
# ============================================================

pipeline = runpy.run_path(
    str(PROJECT_ROOT / "src" / "15_run_pipeline.py")
)

get_engine = pipeline["get_engine"]

invalid_billing_date_mask = pipeline[
    "invalid_billing_date_mask"
]

quarantine_invalid_billing_timestamps = pipeline[
    "quarantine_invalid_billing_timestamps"
]


# ============================================================
# 2. READ THE TEST CSV
# ============================================================

billing = pd.read_csv(
    TEST_FILE,
    dtype=str,
    keep_default_na=False
)


# ============================================================
# 3. VALIDATE TEST RECORD
# ============================================================

if len(billing) != 1:
    raise ValueError("Expected exactly one test record.")

bill = billing.iloc[0]

if bill["bill_id"] != BILL_ID:
    raise ValueError("Unexpected bill ID.")

if bill["payment_status"] != "Paid":
    raise ValueError("Payment status must be Paid.")

if bill["updated_at"] != "":
    raise ValueError("Expected missing updated_at.")


# ============================================================
# 4. DETECT INVALID TIMESTAMP
# ============================================================

invalid_mask = invalid_billing_date_mask(
    billing["updated_at"]
)

if not invalid_mask.all():
    raise ValueError(
        "Test record should have an invalid updated_at."
    )

print("Test bill:", BILL_ID)
print("Payment status:", bill["payment_status"])
print("Updated at:", repr(bill["updated_at"]))
print("Invalid timestamp detected:", bool(invalid_mask.iloc[0]))


# ============================================================
# 5. INSERT INTO QUARANTINE
# ============================================================

engine = get_engine()

quarantine_invalid_billing_timestamps(
    billing,
    engine,
    source_file_name=TEST_FILE.name
)

print("Newer billing quarantine test completed.")
