
from datetime import datetime
import importlib.util
from pathlib import Path

import pandas as pd
from dotenv import dotenv_values
from sqlalchemy import URL, create_engine, text


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_late_arriving_bill_is_recovered_without_moving_watermark(tmp_path):

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

    first_bill_id = "ITEST-FIRST-B002"
    late_bill_id = "ITEST-LATE-B003"

    try:
        # 2. Verify the database and save its original state.
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
                    WHERE bill_id IN (:first_id, :late_id)
                """),
                {
                    "first_id": first_bill_id,
                    "late_id": late_bill_id,
                },
            ).scalar_one()

            assert original_watermark == datetime(1900, 1, 1)
            assert existing_count == 0

        try:
            # 3. Import the actual production pipeline.
            pipeline_file = PROJECT_ROOT / "src" / "15_run_pipeline.py"

            spec = importlib.util.spec_from_file_location(
                "telco_pipeline_late_arrival",
                pipeline_file,
            )

            assert spec is not None
            assert spec.loader is not None

            pipeline = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(pipeline)

            # 4. FIRST INGESTION: Vendor sends B002, updated June 5.
            first_csv = tmp_path / "first_batch.csv"

            pd.DataFrame([
                {
                    "bill_id": first_bill_id,
                    "customer_id": "ITEST-C002",
                    "payment_status": "Paid",
                    "total_amount": 200.00,
                    "created_at": "2026-06-01",
                    "updated_at": "2026-06-05",
                }
            ]).to_csv(first_csv, index=False)

            first_rows_loaded = pipeline.load_billing_raw_incremental(
                engine,
                source_file=first_csv,
            )

            assert first_rows_loaded == 1

            # 5. Verify the first ingestion updated the watermark.
            with engine.connect() as connection:

                watermark_after_first = connection.execute(
                    text("""
                        SELECT last_watermark
                        FROM audit.pipeline_watermark
                        WHERE pipeline_name = 'telco_customer_360'
                          AND source_name = 'billing_transactions'
                    """)
                ).scalar_one()

                assert watermark_after_first == datetime(2026, 6, 5)

            # 6. SECOND INGESTION: Missing B003 arrives late.
            late_csv = tmp_path / "late_batch.csv"

            pd.DataFrame([
                {
                    "bill_id": late_bill_id,
                    "customer_id": "ITEST-C003",
                    "payment_status": "Paid",
                    "total_amount": 150.00,
                    "created_at": "2026-06-02",
                    "updated_at": "2026-06-04",
                }
            ]).to_csv(late_csv, index=False)

            late_rows_loaded = pipeline.load_billing_raw_incremental(
                engine,
                source_file=late_csv,
            )

            # 7. Document the CURRENT behavior: the late bill is skipped.
            assert late_rows_loaded == 1

            # 8. Verify what actually happened in PostgreSQL.
            with engine.connect() as connection:

                first_bill_count = connection.execute(
                    text("""
                        SELECT COUNT(*)
                        FROM raw.billing_transactions
                        WHERE bill_id = :bill_id
                    """),
                    {"bill_id": first_bill_id},
                ).scalar_one()

                late_bill_count = connection.execute(
                    text("""
                        SELECT COUNT(*)
                        FROM raw.billing_transactions
                        WHERE bill_id = :bill_id
                    """),
                    {"bill_id": late_bill_id},
                ).scalar_one()

                final_watermark = connection.execute(
                    text("""
                        SELECT last_watermark
                        FROM audit.pipeline_watermark
                        WHERE pipeline_name = 'telco_customer_360'
                          AND source_name = 'billing_transactions'
                    """)
                ).scalar_one()

                assert first_bill_count == 1
                assert late_bill_count == 1
                assert final_watermark == datetime(2026, 6, 5)

        finally:
            # 9. Remove test records and restore the watermark.
            with engine.begin() as connection:

                connection.execute(
                    text("""
                        DELETE FROM raw.billing_transactions
                        WHERE bill_id IN (:first_id, :late_id)
                    """),
                    {
                        "first_id": first_bill_id,
                        "late_id": late_bill_id,
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
        # 10. Release SQLAlchemy connection resources.
        engine.dispose()
