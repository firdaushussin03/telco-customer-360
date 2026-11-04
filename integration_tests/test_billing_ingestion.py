
from datetime import datetime
import importlib.util
from pathlib import Path

import pandas as pd
from dotenv import dotenv_values
from sqlalchemy import URL, create_engine, text


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_successful_billing_ingestion_commits_both(tmp_path):

    # 1. Read the integration test database settings.
    config = dotenv_values(PROJECT_ROOT / ".env.integration")

    # 2. Reject unexpected database connection settings.
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

    try:
        # 3. Verify the actual database identity and starting state.
        with engine.connect() as connection:

            database_name, db_user = connection.execute(
                text("SELECT current_database(), current_user")
            ).one()

            assert database_name == "telco_test"
            assert db_user == "telco_test_user"

            original_watermark = connection.execute(
                text("""
                    SELECT last_watermark
                    FROM audit.pipeline_watermark
                    WHERE pipeline_name = 'telco_customer_360'
                      AND source_name = 'billing_transactions'
                """)
            ).scalar_one()

            existing_bill_count = connection.execute(
                text("""
                    SELECT COUNT(*)
                    FROM raw.billing_transactions
                    WHERE bill_id = 'ITEST-B001'
                """)
            ).scalar_one()

            assert original_watermark == datetime(1900, 1, 1)
            assert existing_bill_count == 0

        # 4. Import the actual production pipeline module.
        pipeline_file = PROJECT_ROOT / "src" / "15_run_pipeline.py"

        spec = importlib.util.spec_from_file_location(
            "telco_pipeline_integration",
            pipeline_file,
        )

        assert spec is not None
        assert spec.loader is not None

        pipeline = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pipeline)

        # 5. Create a temporary CSV with one valid billing record.
        csv_file = tmp_path / "billing_transactions.csv"

        pd.DataFrame([
            {
                "bill_id": "ITEST-B001",
                "customer_id": "ITEST-C001",
                "payment_status": "Paid",
                "total_amount": 100.00,
                "created_at": "2026-06-01",
                "updated_at": "2026-06-05",
            }
        ]).to_csv(csv_file, index=False)

        try:
            # 6. Execute the REAL billing ingestion function.
            rows_loaded = pipeline.load_billing_raw_incremental(
                engine,
                source_file=csv_file,
            )

            assert rows_loaded == 1

            # 7. Open another connection and verify committed data.
            with engine.connect() as connection:

                saved_bill = connection.execute(
                    text("""
                        SELECT payment_status
                        FROM raw.billing_transactions
                        WHERE bill_id = 'ITEST-B001'
                    """)
                ).scalar_one()

                saved_watermark = connection.execute(
                    text("""
                        SELECT last_watermark
                        FROM audit.pipeline_watermark
                        WHERE pipeline_name = 'telco_customer_360'
                          AND source_name = 'billing_transactions'
                    """)
                ).scalar_one()

                assert saved_bill == "Paid"
                assert saved_watermark == datetime(2026, 6, 5)

        finally:
            # 8. Clean up test data and restore the watermark.
            with engine.begin() as connection:

                connection.execute(
                    text("""
                        DELETE FROM raw.billing_transactions
                        WHERE bill_id = 'ITEST-B001'
                    """)
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
        engine.dispose()
