
from pathlib import Path

import pytest
from dotenv import dotenv_values
from sqlalchemy import URL, create_engine, text


def test_postgresql_transaction_rollback():

    # 1. Locate .env.integration in the project root.
    project_root = Path(__file__).resolve().parents[1]
    env_file = project_root / ".env.integration"

    if not env_file.is_file():
        pytest.fail(".env.integration file was not found")

    # 2. Read database settings from the environment file.
    config = dotenv_values(env_file)

    required_variables = [
        "DB_HOST",
        "DB_PORT",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
    ]

    missing = [
        key for key in required_variables
        if not config.get(key)
    ]

    if missing:
        pytest.fail(f"Missing test database settings: {missing}")

    # 3. Prevent connections to unexpected database settings.
    if (
        config["DB_HOST"] != "127.0.0.1"
        or config["DB_PORT"] != "5437"
        or config["DB_NAME"] != "telco_test"
        or config["DB_USER"] != "telco_test_user"
    ):
        pytest.fail("Refusing to connect to a non-test database")

    # 4. Construct the SQLAlchemy connection URL.
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
        with engine.connect() as connection:

            # 5. Verify the actual connected database and user.
            actual_database, actual_user = connection.execute(
                text("SELECT current_database(), current_user")
            ).one()

            assert actual_database == "telco_test"
            assert actual_user == "telco_test_user"

            # 6. Create a temporary table for this test session.
            connection.execute(
                text("""
                    CREATE TEMP TABLE rollback_probe (
                        bill_id TEXT PRIMARY KEY
                    ) ON COMMIT PRESERVE ROWS
                """)
            )

            connection.commit()

            # 7. Insert a record in a new transaction.
            connection.execute(
                text("""
                    INSERT INTO rollback_probe (bill_id)
                    VALUES ('B001')
                """)
            )

            # 8. Verify B001 is visible before rollback.
            count_before = connection.execute(
                text("SELECT COUNT(*) FROM rollback_probe")
            ).scalar_one()

            assert count_before == 1

            # 9. Undo the uncommitted insertion.
            connection.rollback()

            # 10. Verify PostgreSQL removed the insertion.
            count_after = connection.execute(
                text("SELECT COUNT(*) FROM rollback_probe")
            ).scalar_one()

            assert count_after == 0

    finally:
        engine.dispose()
