import pandas as pd
import os
from pathlib import Path
from getpass import getpass

from sqlalchemy import URL, create_engine, text


# ============================================================
# TELCO CUSTOMER 360 - INCREMENTAL BILLING RAW LOAD
# File: 19_load_billing_raw.py
#
# Purpose:
#   - Read synthetic billing source data
#   - Check the last successful billing watermark
#   - Load only new / changed source rows into RAW
#   - Update the watermark only after a successful load
#
# Incremental key:
#   updated_at
# ============================================================


PROJECT_ROOT = Path(__file__).resolve().parents[1]

SOURCE_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "billing_transactions.csv"
)

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "telco_project")
DB_USER = os.getenv("DB_USER", "postgres")

PIPELINE_NAME = "telco_customer_360"
SOURCE_NAME = "billing_transactions"


def get_engine():
    password = getpass("PostgreSQL password: ")

    connection_url = URL.create(
        drivername="postgresql+psycopg2",
        username=DB_USER,
        password=password,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
    )

    return create_engine(connection_url)


def get_last_watermark(connection):
    query = text("""
        SELECT last_watermark
        FROM audit.pipeline_watermark
        WHERE pipeline_name = :pipeline_name
          AND source_name = :source_name;
    """)

    watermark = connection.execute(
        query,
        {
            "pipeline_name": PIPELINE_NAME,
            "source_name": SOURCE_NAME,
        },
    ).scalar_one_or_none()

    if watermark is None:
        raise RuntimeError(
            "No watermark record found for billing_transactions."
        )

    return pd.Timestamp(watermark)


def update_watermark(connection, new_watermark):
    query = text("""
        UPDATE audit.pipeline_watermark
        SET
            last_watermark = :new_watermark,
            updated_at = CURRENT_TIMESTAMP
        WHERE pipeline_name = :pipeline_name
          AND source_name = :source_name;
    """)

    connection.execute(
        query,
        {
            "new_watermark": new_watermark.to_pydatetime(),
            "pipeline_name": PIPELINE_NAME,
            "source_name": SOURCE_NAME,
        },
    )


def main():
    if not SOURCE_FILE.exists():
        raise FileNotFoundError(
            f"Billing source file not found: {SOURCE_FILE}"
        )

    engine = get_engine()

    billing = pd.read_csv(
        SOURCE_FILE,
        parse_dates=["created_at", "updated_at"],
    )

    print(f"Source rows: {len(billing)}")

    # One transaction protects both the RAW insert and the
    # watermark update. If either fails, neither is committed.
    with engine.begin() as connection:
        last_watermark = get_last_watermark(connection)

        print("Current watermark:", last_watermark)

        incremental_rows = billing[
            billing["updated_at"] > last_watermark
        ].copy()

        print(
            "New / changed rows found:",
            len(incremental_rows),
        )

        if incremental_rows.empty:
            print(
                "No new or changed billing records to load."
            )
            return

        incremental_rows["source_file_name"] = SOURCE_FILE.name

        # ingested_at is omitted so PostgreSQL uses the table's
        # DEFAULT CURRENT_TIMESTAMP.
        incremental_rows.to_sql(
            name="billing_transactions",
            con=connection,
            schema="raw",
            if_exists="append",
            index=False,
            chunksize=1000,
            method="multi",
        )

        new_watermark = incremental_rows["updated_at"].max()

        update_watermark(
            connection,
            new_watermark,
        )

        print(
            "Rows loaded into raw.billing_transactions:",
            len(incremental_rows),
        )
        print("New watermark:", new_watermark)

    print(
        "\nIncremental billing RAW load completed successfully."
    )


if __name__ == "__main__":
    main()
