
import pandas as pd
from pathlib import Path

# Project folder
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Original CSV (read-only)
SOURCE_FILE = (
    PROJECT_ROOT / "data" / "raw" / "billing_transactions.csv"
)

# Separate test CSV
TEST_FILE = (
    PROJECT_ROOT / "data" / "test" / "billing_recovery_invalid.csv"
)

# Read original source
billing = pd.read_csv(
    SOURCE_FILE,
    dtype=str,
    keep_default_na=False
)

# Select an existing bill as a template
template = billing.loc[
    billing["bill_id"] == "B202601-7495-OOKFY"
].copy()

if len(template) != 1:
    raise ValueError("Expected exactly one template bill.")

# Create a NEW test bill
template.loc[:, "bill_id"] = "BTEST-RECOVERY-001"

# Simulate missing updated_at
template.loc[:, "updated_at"] = ""

# Create the test directory
TEST_FILE.parent.mkdir(parents=True, exist_ok=True)

# Avoid accidentally overwriting an existing test
if TEST_FILE.exists():
    raise FileExistsError(f"Test file already exists: {TEST_FILE}")

# Save only one test record
template.to_csv(TEST_FILE, index=False)

print("Test billing CSV created successfully.")
print(f"File: {TEST_FILE}")
print(f"Test records: {len(template)}")
print(template[["bill_id", "created_at", "updated_at"]])
