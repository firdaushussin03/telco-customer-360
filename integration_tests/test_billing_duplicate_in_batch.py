
from datetime import datetime
import importlib.util
from pathlib import Path

import pandas as pd
from dotenv import dotenv_values
from sqlalchemy import URL, create_engine, text


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_duplicate_versions_in_same_csv_are_skipped(tmp_path):

    # 1. Connect only to our isolated test database.
    config = dotenv_values(PROJECT_ROOT / ".env.integration")

    assert config.get("DB_HOST") == "127.0.0.1"
    assert config.get("DB_PORT") == "5437"
    assert config.get("DB_NAME") == "telco_test"
    assert config.get("DB_USER") == "telco_test_user"
    assert config.get("DB_PASSWORD")

    database_url = URL.create(
        drivername="postgresql+psycopg2",
        username=config["DB_USER"],
        password=config["DB_PASSWORD"],
        host=config["DB_HOST"],
        port=int(config["DB_PORT"]),
        database=config["DB_NAME"],
    )

    engine = create_engine(database_url)

    first_bill_id = "ITEST-BATCH-B001"
    second_bill_id = "ITEST-BATCH-B002"

    try:
        # 2. Verify database identity and original state.
        with engine.connect() as connection:

            db_name, db_user = connection.execute(
                text("SELECT current_database(), current_user")
            ).one()

            assert db_name == "telco_test"
            assert db_user == "telco_test_user"

            original_watermark = connection.execute(
                text("""
                    SELECT last_watermark
                    FROM audit.pipeline_watermark
                    WHERE pipeline_name = 'telco_customer_360'
                      AND source_name = 'billing_transactions'
                """)
            ).scalar_one()

            existing_count = connection.execute(
                text("""
                    SELECT COUNT(*)
                    FROM raw.billing_transactions
                    WHERE bill_id IN (:first_id, :second_id)
                """),
                {
                    "first_id": first_bill_id,
                    "second_id": second_bill_id,
                },
            ).scalar_one()

            assert original_watermark == datetime(1900, 1, 1)
            assert existing_count == 0

        try:
            # 3. Import the real production pipeline.
            pipeline_file = PROJECT_ROOT / "src" / "telco_pipeline.py"

            spec = importlib.util.spec_from_file_location(
                "telco_pipeline_batch_duplicates",
                pipeline_file,
            )

            assert spec is not None
            assert spec.loader is not None

            pipeline = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(pipeline)

            # 4. Create a CSV containing 3 rows.
            # B001 is duplicated; B002 is unique.
            csv_file = tmp_path / "duplicate_batch.csv"

            pd.DataFrame([
                {
                    "bill_id": first_bill_id,
                    "customer_id": "ITEST-C001",
                    "payment_status": "Paid",
                    "total_amount": 100.00,
                    "created_at": "2026-06-01",
                    "updated_at": "2026-06-05",
                },
                {
                    "bill_id": first_bill_id,
                    "customer_id": "ITEST-C001",
                    "payment_status": "Paid",
                    "total_amount": 100.00,
                    "created_at": "2026-06-01",
                    "updated_at": "2026-06-05",
                },
                {
                    "bill_id": second_bill_id,
                    "customer_id": "ITEST-C002",
                    "payment_status": "Pending",
                    "total_amount": 150.00,
                    "created_at": "2026-06-01",
                    "updated_at": "2026-06-06",
                },
            ]).to_csv(csv_file, index=False)

            # 5. Execute the actual ingestion function.
            rows_loaded = pipeline.load_billing_raw_incremental(
                engine,
                source_file=csv_file,
            )

            # Three source rows, but only two unique versions.
            assert rows_loaded == 2

            # 6. Verify what PostgreSQL actually stored.
            with engine.connect() as connection:

                bill_versions = connection.execute(
                    text("""
                        SELECT bill_id, payment_status, updated_at
                        FROM raw.billing_transactions
                        WHERE bill_id IN (:first_id, :second_id)
                        ORDER BY bill_id, updated_at
                    """),
                    {
                        "first_id": first_bill_id,
                        "second_id": second_bill_id,
                    },
                ).all()

                watermark_after = connection.execute(
                    text("""
                        SELECT last_watermark
                        FROM audit.pipeline_watermark
                        WHERE pipeline_name = 'telco_customer_360'
                          AND source_name = 'billing_transactions'
                    """)
                ).scalar_one()

                quarantine_count = connection.execute(
                    text("""
                        SELECT COUNT(*)
                        FROM audit.billing_quarantine
                        WHERE bill_id IN (:first_id, :second_id)
                    """),
                    {
                        "first_id": first_bill_id,
                        "second_id": second_bill_id,
                    },
                ).scalar_one()

                assert [tuple(row) for row in bill_versions] == [
                    (
                        first_bill_id,
                        "Paid",
                        datetime(2026, 6, 5),
                    ),
                    (
                        second_bill_id,
                        "Pending",
                        datetime(2026, 6, 6),
                    ),
                ]

                assert watermark_after == datetime(2026, 6, 6)
                assert quarantine_count == 0

        finally:
            # 7. Remove test records and restore the watermark.
            with engine.begin() as connection:

                connection.execute(
                    text("""
                        DELETE FROM raw.billing_transactions
                        WHERE bill_id IN (:first_id, :second_id)
                    """),
                    {
                        "first_id": first_bill_id,
                        "second_id": second_bill_id,
                    },
                )

                result = connection.execute(
                    text("""
                        UPDATE audit.pipeline_watermark
                        SET last_watermark = :original_watermark,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE pipeline_name = 'telco_customer_360'
                          AND source_name = 'billing_transactions'
                    """),
                    {"original_watermark": original_watermark},
                )

                assert result.rowcount == 1

    finally:
        # 8. Release database connection resources.
        engine.dispose()
