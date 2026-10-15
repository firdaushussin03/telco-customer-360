
import pandas as pd
import runpy
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

TEST_FILE = (
    PROJECT_ROOT
    / "data"
    / "test"
    / "billing_recovery_invalid.csv"
)

# Load existing functions without executing the main pipeline.
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

# Read the separate test CSV.
billing = pd.read_csv(
    TEST_FILE,
    dtype=str,
    keep_default_na=False
)

# Validate our test setup.
if len(billing) != 1:
    raise ValueError("Expected exactly one test record.")

if billing.iloc[0]["bill_id"] != "BTEST-RECOVERY-001":
    raise ValueError("Unexpected test bill ID.")

invalid_mask = invalid_billing_date_mask(
    billing["updated_at"]
)

if not invalid_mask.all():
    raise ValueError(
        "Test record should have an invalid updated_at."
    )

print("Test bill:", billing.iloc[0]["bill_id"])
print("Updated at:", repr(billing.iloc[0]["updated_at"]))
print("Invalid timestamp detected:", bool(invalid_mask.iloc[0]))

# Connect to PostgreSQL.
engine = get_engine()

# Quarantine the test record.
quarantine_invalid_billing_timestamps(
    billing,
    engine,
    source_file_name=TEST_FILE.name
)

print("Quarantine test completed.")
