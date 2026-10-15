
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Original rejected test file
INVALID_FILE = (
    PROJECT_ROOT
    / "data"
    / "test"
    / "billing_recovery_invalid.csv"
)

# New corrected test file
CORRECTED_FILE = (
    PROJECT_ROOT
    / "data"
    / "test"
    / "billing_recovery_corrected.csv"
)

# Read the rejected record
billing = pd.read_csv(
    INVALID_FILE,
    dtype=str,
    keep_default_na=False
)

# Verify the expected test bill
if len(billing) != 1:
    raise ValueError("Expected exactly one test record.")

if billing.iloc[0]["bill_id"] != "BTEST-RECOVERY-001":
    raise ValueError("Unexpected bill ID.")

# Simulate a source-system correction
billing.loc[:, "updated_at"] = "2026-01-03"

# Prevent overwriting an existing corrected file
if CORRECTED_FILE.exists():
    raise FileExistsError(
        f"Corrected file already exists: {CORRECTED_FILE}"
    )

# Save the corrected record separately
billing.to_csv(CORRECTED_FILE, index=False)

print("Corrected billing CSV created.")
print(f"File: {CORRECTED_FILE}")

print(
    billing[
        ["bill_id", "created_at", "updated_at"]
    ].to_string(index=False)
)
