
# ============================================================
# TELCO CUSTOMER 360 - REQUIRED TABLE VALIDATION TESTS
# File: tests/test_required_tables.py
# ============================================================

import importlib.util
import pytest

from pathlib import Path
from unittest.mock import MagicMock


# Import the actual initialization script.
SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "58_initialize_if_needed.py"
)

spec = importlib.util.spec_from_file_location(
    "telco_initializer", SCRIPT_PATH
)

initializer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(initializer)


def test_verify_required_tables_all_present():

    # Create a fake database engine.
    engine = MagicMock()

    # Simulate the database connection.
    connection = engine.connect.return_value.__enter__.return_value

    # Pretend PostgreSQL returned all required tables.
    connection.execute.return_value.all.return_value = list(
        initializer.REQUIRED_TABLES
    )

    # Call the actual production function.
    initializer.verify_required_tables(engine)

    # Confirm that the function attempted to connect.
    engine.connect.assert_called_once()


def test_verify_required_tables_missing_customer():

    # Create a fake database engine.
    engine = MagicMock()

    # Simulate the database connection.
    connection = engine.connect.return_value.__enter__.return_value

    # Pretend PostgreSQL has all required tables
    # EXCEPT core.customer.
    fake_existing_tables = (
        initializer.REQUIRED_TABLES
        - {("core", "customer")}
    )

    # Make the fake database return only those tables.
    connection.execute.return_value.all.return_value = list(
        fake_existing_tables
    )

    # Expect the production function to detect the missing table.
    with pytest.raises(
        RuntimeError,
        match=r"core\.customer",
    ):
        initializer.verify_required_tables(engine)

    # Confirm that a database connection was requested.
    engine.connect.assert_called_once()
