
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SOURCE_FILE = (
    PROJECT_ROOT / "data" / "raw" / "billing_transactions.csv"
)

TEST_FILE = (
    PROJECT_ROOT / "data" / "test" / "billing_newer_invalid.csv"
)

BILL_ID = "B202601-0420-BWTPW"

# 1. Read the original CSV.
billing = pd.read_csv(
    SOURCE_FILE,
    dtype=str,
    keep_default_na=False
)

# 2. Select the existing bill.
test_bill = billing.loc[
    billing["bill_id"] == BILL_ID
].copy()

if len(test_bill) != 1:
    raise ValueError("Expected exactly one matching bill.")

# 3. Verify the original bill.
if test_bill.iloc[0]["payment_status"] != "Pending":
    raise ValueError("Original bill must be Pending.")

if test_bill.iloc[0]["updated_at"] != "2026-01-01":
    raise ValueError("Unexpected original updated_at.")

# 4. Simulate an invalid Paid update.
test_bill.loc[:, "payment_status"] = "Paid"
test_bill.loc[:, "updated_at"] = ""

# 5. Save to a separate test file.
TEST_FILE.parent.mkdir(parents=True, exist_ok=True)

if TEST_FILE.exists():
    raise FileExistsError(
        f"Test file already exists: {TEST_FILE}"
    )

test_bill.to_csv(TEST_FILE, index=False)

print("Newer-than-watermark test created.")
print(f"File: {TEST_FILE}")

print(
    test_bill[
        ["bill_id", "payment_status", "created_at", "updated_at"]
    ].to_string(index=False)
)
