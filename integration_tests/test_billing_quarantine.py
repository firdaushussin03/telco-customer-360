
from datetime import datetime
import importlib.util
from pathlib import Path

import pandas as pd
from dotenv import dotenv_values
from sqlalchemy import URL, create_engine, text


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_invalid_timestamp_is_quarantined(tmp_path):

    # 1. Read the isolated test database configuration.
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

    valid_bill_id = "ITEST-VALID-B001"
    invalid_bill_id = "ITEST-INVALID-B002"

    try:
        # 2. Check the database identity and starting state.
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

            original_raw_count = connection.execute(
                text("""
                    SELECT COUNT(*)
                    FROM raw.billing_transactions
                    WHERE bill_id IN (:valid_id, :invalid_id)
                """),
                {
                    "valid_id": valid_bill_id,
                    "invalid_id": invalid_bill_id,
                },
            ).scalar_one()

            original_quarantine_count = connection.execute(
                text("""
                    SELECT COUNT(*)
                    FROM audit.billing_quarantine
                    WHERE bill_id = :invalid_id
                """),
                {"invalid_id": invalid_bill_id},
            ).scalar_one()

            assert original_watermark == datetime(1900, 1, 1)
            assert original_raw_count == 0
            assert original_quarantine_count == 0

        # 3. Import the real production pipeline.
        pipeline_file = PROJECT_ROOT / "src" / "15_run_pipeline.py"

        spec = importlib.util.spec_from_file_location(
            "telco_pipeline_quarantine_test",
            pipeline_file,
        )

        assert spec is not None
        assert spec.loader is not None

        pipeline = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pipeline)

        # 4. Prepare a CSV with one valid and one invalid record.
        csv_file = tmp_path / "billing_transactions.csv"

        pd.DataFrame([
            {
                "bill_id": valid_bill_id,
                "customer_id": "ITEST-C001",
                "payment_status": "Paid",
                "total_amount": 100.00,
                "created_at": "2026-06-01",
                "updated_at": "2026-06-07",
            },
            {
                "bill_id": invalid_bill_id,
                "customer_id": "ITEST-C002",
                "payment_status": "Pending",
                "total_amount": 120.00,
                "created_at": "2026-06-01",
                "updated_at": "not-a-timestamp",
            },
        ]).to_csv(csv_file, index=False)

        try:
            # 5. Run the real incremental ingestion function.
            rows_loaded = pipeline.load_billing_raw_incremental(
                engine,
                source_file=csv_file,
            )

            assert rows_loaded == 1

            # 6. Verify the results in real PostgreSQL.
            with engine.connect() as connection:

                valid_raw_count = connection.execute(
                    text("""
                        SELECT COUNT(*)
                        FROM raw.billing_transactions
                        WHERE bill_id = :bill_id
                    """),
                    {"bill_id": valid_bill_id},
                ).scalar_one()

                invalid_raw_count = connection.execute(
                    text("""
                        SELECT COUNT(*)
                        FROM raw.billing_transactions
                        WHERE bill_id = :bill_id
                    """),
                    {"bill_id": invalid_bill_id},
                ).scalar_one()

                quarantine_row = connection.execute(
                    text("""
                        SELECT status,
                               raw_record ->> 'updated_at'
                        FROM audit.billing_quarantine
                        WHERE bill_id = :bill_id
                          AND source_file_name = :source_file
                    """),
                    {
                        "bill_id": invalid_bill_id,
                        "source_file": csv_file.name,
                    },
                ).one()

                watermark_after = connection.execute(
                    text("""
                        SELECT last_watermark
                        FROM audit.pipeline_watermark
                        WHERE pipeline_name = 'telco_customer_360'
                          AND source_name = 'billing_transactions'
                    """)
                ).scalar_one()

                assert valid_raw_count == 1
                assert invalid_raw_count == 0
                assert quarantine_row[0] == "OPEN"
                assert quarantine_row[1] == "not-a-timestamp"
                assert watermark_after == datetime(2026, 6, 7)

        finally:
            # 7. Clean up test records and restore watermark.
            with engine.begin() as connection:

                connection.execute(
                    text("""
                        DELETE FROM raw.billing_transactions
                        WHERE bill_id IN (:valid_id, :invalid_id)
                    """),
                    {
                        "valid_id": valid_bill_id,
                        "invalid_id": invalid_bill_id,
                    },
                )

                connection.execute(
                    text("""
                        DELETE FROM audit.billing_quarantine
                        WHERE bill_id = :invalid_id
                          AND source_file_name = :source_file
                    """),
                    {
                        "invalid_id": invalid_bill_id,
                        "source_file": csv_file.name,
                    },
                )

                connection.execute(
                    text("""
                        UPDATE audit.pipeline_watermark
                        SET last_watermark = :original_watermark,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE pipeline_name = 'telco_customer_360'
                          AND source_name = 'billing_transactions'
                    """),
                    {"original_watermark": original_watermark},
                )

    finally:
        # 8. Release SQLAlchemy connection resources.
        engine.dispose()
