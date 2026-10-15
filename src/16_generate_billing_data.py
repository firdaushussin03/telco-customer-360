import pandas as pd
import numpy as np
from pathlib import Path

# ============================================================
# TELCO CUSTOMER 360 - SYNTHETIC BILLING DATA GENERATOR
# File: 16_generate_billing_data.py
#
# Grain:
#   1 row = 1 customer bill for 1 billing month
# ============================================================

PROJECT_ROOT = Path(r"C:\Users\mohd5\Documents\telco-customer-360")

SOURCE_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "Telco_customer_churn_services.xlsx"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "billing_transactions.csv"
)

START_MONTH = "2026-01-01"
NUMBER_OF_MONTHS = 6
RANDOM_SEED = 42


def generate_billing_data():
    np.random.seed(RANDOM_SEED)

    services = pd.read_excel(SOURCE_FILE)

    required_columns = [
        "Customer ID",
        "Monthly Charge",
        "Avg Monthly Long Distance Charges",
        "Total Extra Data Charges",
        "Payment Method",
        "Offer",
    ]

    missing_columns = [
        col for col in required_columns
        if col not in services.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    print(f"Customers loaded: {len(services)}")

    billing_months = pd.date_range(
        start=START_MONTH,
        periods=NUMBER_OF_MONTHS,
        freq="MS",
    )

    rows = []

    for month in billing_months:
        for _, customer in services.iterrows():
            customer_id = customer["Customer ID"]

            base_monthly_charge = float(
                customer["Monthly Charge"]
            )

            avg_long_distance = float(
                customer["Avg Monthly Long Distance Charges"]
            )

            total_extra_data = float(
                customer["Total Extra Data Charges"]
            )

            long_distance_multiplier = np.random.uniform(
                0.75,
                1.25,
            )

            long_distance_charge = round(
                avg_long_distance * long_distance_multiplier,
                2,
            )

            if total_extra_data > 0:
                extra_data_charge = float(
                    np.random.choice(
                        [0, 0, 5, 10, 15, 20]
                    )
                )
            else:
                extra_data_charge = 0.00

            if pd.notna(customer["Offer"]):
                discount_amount = float(
                    np.random.choice(
                        [0, 5, 10]
                    )
                )
            else:
                discount_amount = 0.00

            total_amount = round(
                base_monthly_charge
                + long_distance_charge
                + extra_data_charge
                - discount_amount,
                2,
            )

            total_amount = max(total_amount, 0.00)

            payment_status = np.random.choice(
                ["Paid", "Pending", "Failed"],
                p=[0.92, 0.05, 0.03],
            )

            bill_id = (
                f"B{month.strftime('%Y%m')}-"
                f"{customer_id}"
            )

            created_at = (
                month
                + pd.Timedelta(
                    days=int(np.random.randint(0, 4))
                )
            )

            updated_at = created_at

            rows.append(
                {
                    "bill_id": bill_id,
                    "customer_id": customer_id,
                    "billing_date": month.date(),
                    "base_monthly_charge": round(
                        base_monthly_charge,
                        2,
                    ),
                    "long_distance_charge": long_distance_charge,
                    "extra_data_charge": extra_data_charge,
                    "discount_amount": discount_amount,
                    "total_amount": total_amount,
                    "payment_method": customer["Payment Method"],
                    "payment_status": payment_status,
                    "created_at": created_at,
                    "updated_at": updated_at,
                }
            )

    billing = pd.DataFrame(rows)

    expected_rows = len(services) * NUMBER_OF_MONTHS

    print("\nGenerated billing validation")
    print("=" * 50)
    print(f"Expected rows: {expected_rows}")
    print(f"Generated rows: {len(billing)}")
    print(
        "Unique bill IDs:",
        billing["bill_id"].nunique(),
    )
    print(
        "Duplicate bill IDs:",
        billing["bill_id"].duplicated().sum(),
    )
    print(
        "Missing Customer IDs:",
        billing["customer_id"].isnull().sum(),
    )
    print(
        "Negative total amounts:",
        (billing["total_amount"] < 0).sum(),
    )
    print(
        "Billing date range:",
        billing["billing_date"].min(),
        "to",
        billing["billing_date"].max(),
    )

    print("\nPayment status distribution:")
    print(
        billing["payment_status"]
        .value_counts()
        .sort_index()
    )

    if len(billing) != expected_rows:
        raise RuntimeError(
            "Generated row count does not match expected row count."
        )

    if billing["bill_id"].duplicated().any():
        raise RuntimeError(
            "Duplicate bill IDs were generated."
        )

    if billing["customer_id"].isnull().any():
        raise RuntimeError(
            "Missing customer IDs were generated."
        )

    if (billing["total_amount"] < 0).any():
        raise RuntimeError(
            "Negative total amounts were generated."
        )

    billing.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    print("\nBilling data generated successfully.")
    print(f"Output file: {OUTPUT_FILE}")


if __name__ == "__main__":
    generate_billing_data()
