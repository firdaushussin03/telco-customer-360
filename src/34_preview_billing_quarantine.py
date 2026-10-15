
import pandas as pd
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

BILLING_SOURCE_FILE = (
    PROJECT_ROOT / "data" / "raw" / "billing_transactions.csv"
)


# ============================================================
# 1. READ THE BILLING SOURCE
# ============================================================

billing = pd.read_csv(BILLING_SOURCE_FILE)

print(f"Total source rows: {len(billing)}")


# ============================================================
# 2. SIMULATE ONE INVALID RECORD (IN MEMORY ONLY)
# ============================================================

billing.loc[0, "updated_at"] = None


# ============================================================
# 3. CHECK REQUIRED VALUES
# ============================================================

def is_missing(value):
    return pd.isna(value) or str(value).strip() == ""


created_dates = pd.to_datetime(
    billing["created_at"],
    errors="coerce"
)

updated_dates = pd.to_datetime(
    billing["updated_at"],
    errors="coerce"
)

reasons = []

for index, row in billing.iterrows():

    errors = []

    if is_missing(row["bill_id"]):
        errors.append("Missing bill_id")

    if is_missing(row["customer_id"]):
        errors.append("Missing customer_id")

    if pd.isna(created_dates.loc[index]):
        errors.append("Missing or invalid created_at")

    if pd.isna(updated_dates.loc[index]):
        errors.append("Missing or invalid updated_at")

    if (
        pd.notna(created_dates.loc[index])
        and pd.notna(updated_dates.loc[index])
        and updated_dates.loc[index] < created_dates.loc[index]
    ):
        errors.append("updated_at earlier than created_at")

    reasons.append("; ".join(errors))


# ============================================================
# 4. SEPARATE VALID AND INVALID RECORDS
# ============================================================

rejection_reasons = pd.Series(
    reasons,
    index=billing.index
)

invalid_mask = rejection_reasons.ne("")

valid_rows = billing.loc[~invalid_mask].copy()

invalid_rows = billing.loc[invalid_mask].copy()

invalid_rows["source_row_number"] = invalid_rows.index + 2

invalid_rows["rejection_reason"] = rejection_reasons.loc[
    invalid_mask
]



# ============================================================
# 5. PREVIEW RESULTS
# ============================================================

print("\n" + "=" * 50)
print("BILLING QUARANTINE PREVIEW")
print("=" * 50)

print(f"Total source rows : {len(billing)}")
print(f"Valid records     : {len(valid_rows)}")
print(f"Invalid records   : {len(invalid_rows)}")

print("\nRECORDS THAT WOULD BE QUARANTINED")
print("-" * 50)

if invalid_rows.empty:
    print("No invalid records found.")

else:
    for _, row in invalid_rows.iterrows():

        updated_at = (
            "MISSING"
            if pd.isna(row["updated_at"])
            else row["updated_at"]
        )

        print(f"Source Row       : {row['source_row_number']}")
        print(f"Bill ID          : {row['bill_id']}")
        print(f"Updated At       : {updated_at}")
        print(f"Rejection Reason : {row['rejection_reason']}")
        print("-" * 50)
