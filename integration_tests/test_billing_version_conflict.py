from datetime import datetime
import importlib.util
from pathlib import Path

import pandas as pd
import pytest
from dotenv import dotenv_values
from sqlalchemy import URL, create_engine, text


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_conflicting_versions_in_same_csv_are_rejected(tmp_path):
    # 1. Connect only to the isolated integration database.
    config = dotenv_values(PROJECT_ROOT / '.env.integration')

    assert config.get('DB_HOST') == '127.0.0.1'
    assert config.get('DB_PORT') == '5437'
    assert config.get('DB_NAME') == 'telco_test'
    assert config.get('DB_USER') == 'telco_test_user'
    assert config.get('DB_PASSWORD')

    database_url = URL.create(
        drivername='postgresql+psycopg2',
        username=config['DB_USER'],
        password=config['DB_PASSWORD'],
        host=config['DB_HOST'],
        port=int(config['DB_PORT']),
        database=config['DB_NAME'],
    )
    engine = create_engine(database_url)

    conflicting_id = 'ITEST-CONFLICT-B001'
    other_id = 'ITEST-CONFLICT-B002'

    try:
        # 2. Confirm database identity and save original watermark.
        with engine.connect() as connection:
            db_name, db_user = connection.execute(
                text('SELECT current_database(), current_user')
            ).one()
            assert db_name == 'telco_test'
            assert db_user == 'telco_test_user'

            original_watermark = connection.execute(
                text('''
                    SELECT last_watermark
                    FROM audit.pipeline_watermark
                    WHERE pipeline_name = 'telco_customer_360'
                      AND source_name = 'billing_transactions'
                ''')
            ).scalar_one()

            existing_count = connection.execute(
                text('''
                    SELECT COUNT(*)
                    FROM raw.billing_transactions
                    WHERE bill_id IN (:conflicting_id, :other_id)
                '''),
                {'conflicting_id': conflicting_id, 'other_id': other_id},
            ).scalar_one()

            assert original_watermark == datetime(1900, 1, 1)
            assert existing_count == 0

        try:
            # 3. Import the same production file used by other tests.
            pipeline_file = PROJECT_ROOT / 'src' / 'telco_pipeline.py'
            spec = importlib.util.spec_from_file_location(
                'telco_pipeline_version_conflict', pipeline_file
            )
            assert spec is not None and spec.loader is not None
            pipeline = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(pipeline)

            # 4. Same bill_id and updated_at, but conflicting statuses.
            # B002 is otherwise valid; it must not be partially inserted.
            csv_file = tmp_path / 'conflicting_versions.csv'
            pd.DataFrame([
                {
                    'bill_id': conflicting_id,
                    'customer_id': 'ITEST-C001',
                    'payment_status': 'Pending',
                    'total_amount': 100.00,
                    'created_at': '2026-06-01',
                    'updated_at': '2026-06-05',
                },
                {
                    'bill_id': conflicting_id,
                    'customer_id': 'ITEST-C001',
                    'payment_status': 'Paid',
                    'total_amount': 100.00,
                    'created_at': '2026-06-01',
                    'updated_at': '2026-06-05',
                },
                {
                    'bill_id': other_id,
                    'customer_id': 'ITEST-C002',
                    'payment_status': 'Paid',
                    'total_amount': 150.00,
                    'created_at': '2026-06-01',
                    'updated_at': '2026-06-06',
                },
            ]).to_csv(csv_file, index=False)

            # 5. Expect a clear error instead of choosing a status.
            with pytest.raises(ValueError, match='Conflicting source records'):
                pipeline.load_billing_raw_incremental(
                    engine, source_file=csv_file
                )

            # 6. Verify the conflicting batch did not change RAW/watermark.
            with engine.connect() as connection:
                bill_count = connection.execute(
                    text('''
                        SELECT COUNT(*)
                        FROM raw.billing_transactions
                        WHERE bill_id IN (:conflicting_id, :other_id)
                    '''),
                    {'conflicting_id': conflicting_id, 'other_id': other_id},
                ).scalar_one()
                watermark_after = connection.execute(
                    text('''
                        SELECT last_watermark
                        FROM audit.pipeline_watermark
                        WHERE pipeline_name = 'telco_customer_360'
                          AND source_name = 'billing_transactions'
                    ''')
                ).scalar_one()
                quarantine_count = connection.execute(
                    text('''
                        SELECT COUNT(*)
                        FROM audit.billing_quarantine
                        WHERE bill_id IN (:conflicting_id, :other_id)
                    '''),
                    {'conflicting_id': conflicting_id, 'other_id': other_id},
                ).scalar_one()

                assert bill_count == 0
                assert watermark_after == original_watermark
                assert quarantine_count == 0  # Conflicts raise, not quarantine.

        finally:
            # 7. Restore test state even if an assertion fails.
            with engine.begin() as connection:
                connection.execute(
                    text('''
                        DELETE FROM raw.billing_transactions
                        WHERE bill_id IN (:conflicting_id, :other_id)
                    '''),
                    {'conflicting_id': conflicting_id, 'other_id': other_id},
                )
                result = connection.execute(
                    text('''
                        UPDATE audit.pipeline_watermark
                        SET last_watermark = :original_watermark,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE pipeline_name = 'telco_customer_360'
                          AND source_name = 'billing_transactions'
                    '''),
                    {'original_watermark': original_watermark},
                )
                assert result.rowcount == 1
    finally:
        engine.dispose()
