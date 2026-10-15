
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

INVALID_FILE = (
    PROJECT_ROOT
    / "data"
    / "test"
    / "billing_existing_invalid.csv"
)

CORRECTED_FILE = (
    PROJECT_ROOT
    / "data"
    / "test"
    / "billing_existing_corrected.csv"
)

BILL_ID = "B202601-0215-BQKGS"

# 1. Read the quarantined test record.
billing = pd.read_csv(
    INVALID_FILE,
    dtype=str,
    keep_default_na=False
)

# 2. Verify the expected bill.
if len(billing) != 1:
    raise ValueError("Expected exactly one test record.")

if billing.iloc[0]["bill_id"] != BILL_ID:
    raise ValueError("Unexpected bill ID.")

if billing.iloc[0]["payment_status"] != "Paid":
    raise ValueError("Payment status should be Paid.")

if billing.iloc[0]["updated_at"] != "":
    raise ValueError("Expected an empty updated_at.")

# 3. Apply the simulated source-system correction.
billing.loc[:, "updated_at"] = "2026-03-02"

# 4. Prevent accidental overwrite.
if CORRECTED_FILE.exists():
    raise FileExistsError(
        f"Corrected file already exists: {CORRECTED_FILE}"
    )

# 5. Save the corrected record.
billing.to_csv(CORRECTED_FILE, index=False)

print("Existing billing update corrected successfully.")
print(f"File: {CORRECTED_FILE}")

print(
    billing[
        ["bill_id", "payment_status", "created_at", "updated_at"]
    ].to_string(index=False)
)
