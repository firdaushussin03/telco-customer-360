
import pandas as pd
import runpy
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

TEST_FILE = (
    PROJECT_ROOT
    / "data"
    / "test"
    / "billing_existing_invalid.csv"
)

BILL_ID = "B202601-0215-BQKGS"

# 1. Load reusable functions from the main pipeline.
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

# 2. Read the test CSV.
billing = pd.read_csv(
    TEST_FILE,
    dtype=str,
    keep_default_na=False
)

# 3. Verify the test record.
if len(billing) != 1:
    raise ValueError("Expected exactly one test record.")

if billing.iloc[0]["bill_id"] != BILL_ID:
    raise ValueError("Unexpected bill ID.")

if billing.iloc[0]["payment_status"] != "Paid":
    raise ValueError("Test payment status must be Paid.")

# 4. Detect the invalid updated_at.
invalid_mask = invalid_billing_date_mask(
    billing["updated_at"]
)

if not invalid_mask.all():
    raise ValueError(
        "Test record should contain an invalid updated_at."
    )

print("Test bill:", BILL_ID)
print("Payment status:", billing.iloc[0]["payment_status"])
print("Updated at:", repr(billing.iloc[0]["updated_at"]))
print("Invalid timestamp detected:", bool(invalid_mask.iloc[0]))

# 5. Connect to PostgreSQL.
engine = get_engine()

# 6. Save the invalid update into quarantine.
quarantine_invalid_billing_timestamps(
    billing,
    engine,
    source_file_name=TEST_FILE.name
)

print("Existing bill quarantine test completed.")
