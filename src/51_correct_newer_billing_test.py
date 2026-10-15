
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

INVALID_FILE = (
    PROJECT_ROOT
    / "data"
    / "test"
    / "billing_newer_invalid.csv"
)

CORRECTED_FILE = (
    PROJECT_ROOT
    / "data"
    / "test"
    / "billing_newer_corrected.csv"
)

BILL_ID = "B202601-0420-BWTPW"

# ============================================================
# 1. READ THE INVALID TEST RECORD
# ============================================================

billing = pd.read_csv(
    INVALID_FILE,
    dtype=str,
    keep_default_na=False
)

# ============================================================
# 2. VERIFY THE TEST RECORD
# ============================================================

if len(billing) != 1:
    raise ValueError("Expected exactly one test record.")

if billing.iloc[0]["bill_id"] != BILL_ID:
    raise ValueError("Unexpected bill ID.")

if billing.iloc[0]["payment_status"] != "Paid":
    raise ValueError("Payment status should be Paid.")

if billing.iloc[0]["updated_at"] != "":
    raise ValueError("Expected missing updated_at.")

# ============================================================
# 3. APPLY THE SOURCE CORRECTION
# ============================================================

billing.loc[:, "updated_at"] = "2026-06-08"

# ============================================================
# 4. SAVE THE CORRECTED CSV
# ============================================================

if CORRECTED_FILE.exists():
    raise FileExistsError(
        f"Corrected file already exists: {CORRECTED_FILE}"
    )

billing.to_csv(CORRECTED_FILE, index=False)

print("Newer billing update corrected successfully.")
print(f"File: {CORRECTED_FILE}")

print(
    billing[
        ["bill_id", "payment_status", "created_at", "updated_at"]
    ].to_string(index=False)
)
