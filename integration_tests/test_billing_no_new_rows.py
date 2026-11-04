
from datetime import datetime
import importlib.util
from pathlib import Path

import pandas as pd
from dotenv import dotenv_values
from sqlalchemy import URL, create_engine, text


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_billing_ingestion_skips_old_and_equal_records(tmp_path):

    # 1. Read integration test database configuration.
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

    test_watermark = datetime(2026, 6, 5)

    try:
        # 2. Verify the database and original state.
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

            original_bill_count = connection.execute(
                text("""
                    SELECT COUNT(*)
                    FROM raw.billing_transactions
                    WHERE bill_id IN (
                        'ITEST-OLD-B001',
                        'ITEST-EQUAL-B002'
                    )
                """)
            ).scalar_one()

            assert original_watermark == datetime(1900, 1, 1)
            assert original_bill_count == 0

        try:
            # 3. Set a test watermark to June 5, 2026.
            with engine.begin() as connection:

                result = connection.execute(
                    text("""
                        UPDATE audit.pipeline_watermark
                        SET last_watermark = :test_watermark,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE pipeline_name = 'telco_customer_360'
                          AND source_name = 'billing_transactions'
                    """),
                    {"test_watermark": test_watermark},
                )

                assert result.rowcount == 1

                # Seed RAW with versions already received previously.
                connection.execute(
                    text("""
                        INSERT INTO raw.billing_transactions (
                            bill_id,
                            customer_id,
                            payment_status,
                            total_amount,
                            created_at,
                            updated_at,
                            source_file_name
                        )
                        VALUES
                        (
                            'ITEST-OLD-B001',
                            'ITEST-C001',
                            'Paid',
                            100.00,
                            '2026-06-01',
                            '2026-06-04',
                            'test_seed'
                        ),
                        (
                            'ITEST-EQUAL-B002',
                            'ITEST-C002',
                            'Pending',
                            120.00,
                            '2026-06-01',
                            '2026-06-05',
                            'test_seed'
                        )
                    """)
                )

            # 4. Import the REAL production pipeline.
            pipeline_file = PROJECT_ROOT / "src" / "15_run_pipeline.py"

            spec = importlib.util.spec_from_file_location(
                "telco_pipeline_no_new_rows",
                pipeline_file,
            )

            assert spec is not None
            assert spec.loader is not None

            pipeline = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(pipeline)

            # 5. Create a temporary CSV with two older/equal records.
            csv_file = tmp_path / "billing_transactions.csv"

            pd.DataFrame([
                {
                    "bill_id": "ITEST-OLD-B001",
                    "customer_id": "ITEST-C001",
                    "payment_status": "Paid",
                    "total_amount": 100.00,
                    "created_at": "2026-06-01",
                    "updated_at": "2026-06-04",
                },
                {
                    "bill_id": "ITEST-EQUAL-B002",
                    "customer_id": "ITEST-C002",
                    "payment_status": "Pending",
                    "total_amount": 120.00,
                    "created_at": "2026-06-01",
                    "updated_at": "2026-06-05",
                },
            ]).to_csv(csv_file, index=False)

            # 6. Execute the real incremental ingestion function.
            rows_loaded = pipeline.load_billing_raw_incremental(
                engine,
                source_file=csv_file,
            )

            assert rows_loaded == 0

            # 7. Verify PostgreSQL did not insert either record.
            with engine.connect() as connection:

                bill_count_after = connection.execute(
                    text("""
                        SELECT COUNT(*)
                        FROM raw.billing_transactions
                        WHERE bill_id IN (
                            'ITEST-OLD-B001',
                            'ITEST-EQUAL-B002'
                        )
                    """)
                ).scalar_one()

                watermark_after = connection.execute(
                    text("""
                        SELECT last_watermark
                        FROM audit.pipeline_watermark
                        WHERE pipeline_name = 'telco_customer_360'
                          AND source_name = 'billing_transactions'
                    """)
                ).scalar_one()

                quarantine_count_after = connection.execute(
                    text("""
                        SELECT COUNT(*)
                        FROM audit.billing_quarantine
                        WHERE bill_id IN (
                            'ITEST-OLD-B001',
                            'ITEST-EQUAL-B002'
                        )
                    """)
                ).scalar_one()

                assert bill_count_after == 2
                assert watermark_after == test_watermark
                assert quarantine_count_after == 0

        finally:
            # 8. Restore the database's original test state.
            with engine.begin() as connection:

                connection.execute(
                    text("""
                        DELETE FROM raw.billing_transactions
                        WHERE bill_id IN (
                            'ITEST-OLD-B001',
                            'ITEST-EQUAL-B002'
                        )
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
        # 9. Dispose of the SQLAlchemy connection pool.
        engine.dispose()
