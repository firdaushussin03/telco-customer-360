import pandas as pd
import os
from pathlib import Path
from getpass import getpass
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

BASE_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "telco_project")
DB_USER = os.getenv("DB_USER", "postgres")

LOAD_CONFIG = {
    "demographics": {
        "file": "Telco_customer_churn_demographics.xlsx",
        "columns": {
            "Customer ID": "customer_id",
            "Count": "count",
            "Gender": "gender",
            "Age": "age",
            "Under 30": "under_30",
            "Senior Citizen": "senior_citizen",
            "Married": "married",
            "Dependents": "dependents",
            "Number of Dependents": "number_of_dependents",
        },
    },
    "location": {
        "file": "Telco_customer_churn_location.xlsx",
        "columns": {
            "Location ID": "location_id",
            "Customer ID": "customer_id",
            "Count": "count",
            "Country": "country",
            "State": "state",
            "City": "city",
            "Zip Code": "zip_code",
            "Lat Long": "lat_long",
            "Latitude": "latitude",
            "Longitude": "longitude",
        },
    },
    "population": {
        "file": "Telco_customer_churn_population.xlsx",
        "columns": {
            "ID": "id",
            "Zip Code": "zip_code",
            "Population": "population",
        },
    },
    "services": {
        "file": "Telco_customer_churn_services.xlsx",
        "columns": {
            "Service ID": "service_id",
            "Customer ID": "customer_id",
            "Count": "count",
            "Quarter": "quarter",
            "Referred a Friend": "referred_a_friend",
            "Number of Referrals": "number_of_referrals",
            "Tenure in Months": "tenure_in_months",
            "Offer": "offer",
            "Phone Service": "phone_service",
            "Avg Monthly Long Distance Charges": "avg_monthly_long_distance_charges",
            "Multiple Lines": "multiple_lines",
            "Internet Service": "internet_service",
            "Internet Type": "internet_type",
            "Avg Monthly GB Download": "avg_monthly_gb_download",
            "Online Security": "online_security",
            "Online Backup": "online_backup",
            "Device Protection Plan": "device_protection_plan",
            "Premium Tech Support": "premium_tech_support",
            "Streaming TV": "streaming_tv",
            "Streaming Movies": "streaming_movies",
            "Streaming Music": "streaming_music",
            "Unlimited Data": "unlimited_data",
            "Contract": "contract",
            "Paperless Billing": "paperless_billing",
            "Payment Method": "payment_method",
            "Monthly Charge": "monthly_charge",
            "Total Charges": "total_charges",
            "Total Refunds": "total_refunds",
            "Total Extra Data Charges": "total_extra_data_charges",
            "Total Long Distance Charges": "total_long_distance_charges",
            "Total Revenue": "total_revenue",
        },
    },
    "status": {
        "file": "Telco_customer_churn_status.xlsx",
        "columns": {
            "Status ID": "status_id",
            "Customer ID": "customer_id",
            "Count": "count",
            "Quarter": "quarter",
            "Satisfaction Score": "satisfaction_score",
            "Customer Status": "customer_status",
            "Churn Label": "churn_label",
            "Churn Value": "churn_value",
            "Churn Score": "churn_score",
            "CLTV": "cltv",
            "Churn Category": "churn_category",
            "Churn Reason": "churn_reason",
        },
    },
}


def get_engine():
    password = os.getenv("DB_PASSWORD") or getpass("PostgreSQL password: ")

    connection_url = URL.create(
        drivername="postgresql+psycopg2",
        username=DB_USER,
        password=password,
        host=DB_HOST,
        port=int(DB_PORT),
        database=DB_NAME,
    )

    return create_engine(connection_url)


def get_table_count(connection, table_name):
    return connection.execute(
        text(f"SELECT COUNT(*) FROM raw.{table_name}")
    ).scalar_one()

def load_table(connection, table_name, config):
    file_path = BASE_DIR / config["file"]

    print("\n" + "=" * 70)
    print(f"LOADING: {file_path.name} -> raw.{table_name}")
    print("=" * 70)

    if not file_path.exists():
        raise FileNotFoundError(f"Source file not found: {file_path}")

    existing_rows = get_table_count(connection, table_name)

    if existing_rows > 0:
        raise RuntimeError(
            f"raw.{table_name} already contains {existing_rows} rows. "
            "Load stopped to prevent duplicates."
        )

    df = pd.read_excel(file_path)
    df = df.rename(columns=config["columns"])
    df["source_file_name"] = file_path.name

    df.to_sql(
        name=table_name,
        con=connection,
        schema="raw",
        if_exists="append",
        index=False,
        chunksize=1000,
        method="multi",
    )

    loaded_rows = get_table_count(connection, table_name)

    print(f"Source rows: {len(df)}")
    print(f"Database rows: {loaded_rows}")

    if loaded_rows != len(df):
        raise RuntimeError(
            f"Row-count validation failed for raw.{table_name}."
        )

    print("Load validation successful.")
    
def validate_source_files():
    missing_files = []

    for config in LOAD_CONFIG.values():
        file_path = BASE_DIR / config["file"]

        if not file_path.is_file():
            missing_files.append(str(file_path))

    if missing_files:
        raise FileNotFoundError(
            "Missing Excel source files:\n"
            + "\n".join(missing_files)
        )

    print("All five Excel source files found.")

def main():
    validate_source_files()

    engine = get_engine()

    with engine.begin() as connection:

        connection.execute(text("SELECT 1"))
        print("Database connection successful.")

        for table_name, config in LOAD_CONFIG.items():
            load_table(connection, table_name, config)

    print("\nALL RAW TABLES LOADED SUCCESSFULLY")

if __name__ == "__main__":
    main()
