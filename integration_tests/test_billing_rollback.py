
from datetime import datetime
import importlib.util
from pathlib import Path

import pandas as pd
import pytest
from dotenv import dotenv_values
from sqlalchemy import URL, create_engine, text


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_billing_ingestion_rolls_back_on_failure(tmp_path, monkeypatch):

    # 1. Read settings for our isolated test database.
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

    try:
        # 2. Verify the database and record its initial state.
        with engine.connect() as connection:

            actual_database, actual_user = connection.execute(
                text("SELECT current_database(), current_user")
            ).one()

            assert actual_database == "telco_test"
            assert actual_user == "telco_test_user"

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
                    WHERE bill_id = 'ITEST-ROLLBACK-B001'
                """)
            ).scalar_one()

            assert original_watermark == datetime(1900, 1, 1)
            assert original_bill_count == 0

        # 3. Import the REAL production pipeline.
        pipeline_file = PROJECT_ROOT / "src" / "telco_pipeline.py"

        spec = importlib.util.spec_from_file_location(
            "telco_pipeline_rollback_test",
            pipeline_file,
        )

        assert spec is not None
        assert spec.loader is not None

        pipeline = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pipeline)

        # 4. Create a temporary CSV containing one valid bill.
        csv_file = tmp_path / "billing_transactions.csv"

        pd.DataFrame([
            {
                "bill_id": "ITEST-ROLLBACK-B001",
                "customer_id": "ITEST-C001",
                "payment_status": "Paid",
                "total_amount": 100.00,
                "created_at": "2026-06-01",
                "updated_at": "2026-06-06",
            }
        ]).to_csv(csv_file, index=False)

        # 5. Save the actual watermark update function.
        real_update_watermark = pipeline.update_billing_watermark

        # 6. Inject an error AFTER the real UPDATE executes.
        def update_then_fail(connection, new_watermark):

            real_update_watermark(connection, new_watermark)

            raise RuntimeError(
                "Injected failure before commit"
            )

        monkeypatch.setattr(
            pipeline,
            "update_billing_watermark",
            update_then_fail,
        )

        try:
            # 7. Run real ingestion and expect the injected error.
            with pytest.raises(
                RuntimeError,
                match="Injected failure before commit",
            ):
                pipeline.load_billing_raw_incremental(
                    engine,
                    source_file=csv_file,
                )

            # 8. Verify PostgreSQL rolled back BOTH changes.
            with engine.connect() as connection:

                bill_count_after = connection.execute(
                    text("""
                        SELECT COUNT(*)
                        FROM raw.billing_transactions
                        WHERE bill_id = 'ITEST-ROLLBACK-B001'
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

                assert bill_count_after == 0
                assert watermark_after == original_watermark

        finally:
            # 9. Attempt cleanup even if the rollback test fails.
            with engine.begin() as connection:

                connection.execute(
                    text("""
                        DELETE FROM raw.billing_transactions
                        WHERE bill_id = 'ITEST-ROLLBACK-B001'
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
        # 10. Dispose of SQLAlchemy's connection pool.
        engine.dispose()
