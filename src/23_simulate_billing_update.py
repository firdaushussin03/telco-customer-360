import pandas as pd
from pathlib import Path


# ============================================================
# TELCO CUSTOMER 360 - SIMULATE BILLING UPDATE
# File: 23_simulate_billing_update.py
#
# Purpose:
#   - Simulate a source-system bill changing
#   - Change one Pending bill to Paid
#   - Move updated_at forward so the incremental loader
#     can detect the changed record
# ============================================================


PROJECT_ROOT = Path(
    r"C:\Users\mohd5\Documents\telco-customer-360"
)

BILLING_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "billing_transactions.csv"
)


def main():

    billing = pd.read_csv(
        BILLING_FILE,
        parse_dates=[
            "created_at",
            "updated_at"
        ]
    )

    # Find one Pending bill.
    pending_rows = billing[
        billing["payment_status"] == "Pending"
    ]

    if pending_rows.empty:
        raise RuntimeError(
            "No Pending billing record found."
        )

    # Select the first Pending record.
    row_index = pending_rows.index[0]

    bill_id = billing.loc[
        row_index,
        "bill_id"
    ]

    old_status = billing.loc[
        row_index,
        "payment_status"
    ]

    old_updated_at = billing.loc[
        row_index,
        "updated_at"
    ]

    # Make sure the new updated_at is later than
    # every current source timestamp.
    new_updated_at = (
        billing["updated_at"].max()
        + pd.Timedelta(days=1)
    )

    # Simulate payment being completed.
    billing.loc[
        row_index,
        "payment_status"
    ] = "Paid"

    billing.loc[
        row_index,
        "updated_at"
    ] = new_updated_at

    billing.to_csv(
        BILLING_FILE,
        index=False
    )

    print("Billing update simulated successfully.")
    print()
    print("Bill ID:", bill_id)
    print("Old status:", old_status)
    print("New status: Paid")
    print("Old updated_at:", old_updated_at)
    print("New updated_at:", new_updated_at)


if __name__ == "__main__":
    main()