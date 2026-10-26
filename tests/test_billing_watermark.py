
# ============================================================
# TELCO CUSTOMER 360 - BILLING WATERMARK TESTS
# File: tests/test_billing_watermark.py
# ============================================================

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock
from datetime import datetime
import pytest


# Import the real initialization script.
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


def test_verify_billing_watermark_missing():

    # Create a fake database engine.
    engine = MagicMock()

    # Simulate the database connection.
    connection = engine.connect.return_value.__enter__.return_value

    # Pretend PostgreSQL returned no watermark.
    connection.execute.return_value.scalar_one_or_none.return_value = None

    # Expect the actual function to reject the missing watermark.
    with pytest.raises(
        RuntimeError,
        match="billing watermark record is missing",
    ):
        initializer.verify_billing_watermark(engine)

    # Confirm that a connection was requested.
    engine.connect.assert_called_once()


def test_verify_billing_watermark_exists():

    # Create a fake database engine.
    engine = MagicMock()

    # Simulate the database connection.
    connection = engine.connect.return_value.__enter__.return_value

    # Pretend PostgreSQL returned an existing watermark.
    fake_watermark = datetime(2026, 6, 4, 0, 0, 0)

    connection.execute.return_value.scalar_one_or_none.return_value = (
        fake_watermark
    )

    # Run the actual production function.
    # It should NOT raise RuntimeError.
    initializer.verify_billing_watermark(engine)

    # Verify that a connection was requested.
    engine.connect.assert_called_once()

