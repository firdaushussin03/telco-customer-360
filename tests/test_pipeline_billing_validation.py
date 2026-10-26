
# ============================================================
# TELCO CUSTOMER 360 - PIPELINE BILLING VALIDATION TESTS
# File: tests/test_pipeline_billing_validation.py
# ============================================================

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock
import pandas as pd
import pytest


# Locate the actual Docker pipeline orchestrator.
SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "15_run_pipeline.py"
)

# Import file 15 without executing main().
spec = importlib.util.spec_from_file_location(
    "telco_pipeline",
    SCRIPT_PATH,
)

pipeline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pipeline)


def test_invalid_billing_date_mask():

    # Simulate values received from a billing source.
    updated_at = pd.Series([
        "2026-06-08",
        None,
        "not_a_date",
        "2026-02-30",
        "2026/06/08",
    ])

    # Execute the actual validation function from file 15.
    invalid_mask = pipeline.invalid_billing_date_mask(
        updated_at
    )

    # Convert the boolean results into a Python list.
    actual_result = invalid_mask.tolist()

    # False = valid date, True = invalid date.
    expected_result = [
        False,
        True,
        True,
        True,
        True,
    ]

    assert actual_result == expected_result


def test_quarantine_missing_updated_at():

    # 1. Simulate billing data from a vendor.
    billing = pd.DataFrame({
        "bill_id": ["B001", "B002"],
        "customer_id": ["C001", "C002"],
        "updated_at": ["2026-06-08", None],
    })

    # 2. Simulate a database engine and connection.
    engine = MagicMock()

    connection = (
        engine.begin.return_value
        .__enter__.return_value
    )

    # Simulate PostgreSQL reporting one inserted row.
    connection.execute.return_value.rowcount = 1

    # 3. Call the actual quarantine function.
    inserted_count = (
        pipeline.quarantine_invalid_billing_timestamps(
            billing,
            engine,
            source_file_name="test_billing.csv",
        )
    )

    # 4. Verify a database insert was attempted once.
    connection.execute.assert_called_once()

    # 5. Inspect the parameters sent to the SQL query.
    sql_query, parameters = connection.execute.call_args.args

    assert parameters["bill_id"] == "B002"
    assert parameters["customer_id"] == "C002"

    assert (
        parameters["source_file_name"]
        == "test_billing.csv"
    )

    assert (
        parameters["rejection_reason"]
        == "Missing or invalid updated_at"
    )

    # 6. Verify the function reports one inserted row.
    assert inserted_count == 1


def test_quarantine_no_invalid_timestamps():

    # Simulate billing records with valid timestamps.
    billing = pd.DataFrame({
        "bill_id": ["B001", "B002"],
        "customer_id": ["C001", "C002"],
        "updated_at": [
            "2026-06-08",
            "2026-06-09",
        ],
    })

    # Create a fake database engine.
    engine = MagicMock()

    # Execute the real quarantine function.
    inserted_count = (
        pipeline.quarantine_invalid_billing_timestamps(
            billing,
            engine,
            source_file_name="test_billing.csv",
        )
    )

    # No records should be quarantined.
    assert inserted_count == 0

    # No quarantine database transaction should start.
    engine.begin.assert_not_called()


def test_validate_billing_source_valid_records():

    # 1. Simulate valid billing source records.
    billing = pd.DataFrame({
        "bill_id": ["B001", "B002"],
        "customer_id": ["C001", "C002"],
        "created_at": [
            "2026-06-01",
            "2026-06-06",
        ],
        "updated_at": [
            "2026-06-05",
            "2026-06-06",
        ],
    })

    # 2. Execute the actual production validation function.
    validated_billing = pipeline.validate_billing_source(
        billing
    )

    # 3. Both records should pass validation.
    assert len(validated_billing) == 2

    assert validated_billing["bill_id"].tolist() == [
        "B001",
        "B002",
    ]

    # 4. Date columns should be converted to datetime.
    assert pd.api.types.is_datetime64_any_dtype(
        validated_billing["created_at"]
    )

    assert pd.api.types.is_datetime64_any_dtype(
        validated_billing["updated_at"]
    )


def test_validate_billing_source_missing_customer_id():

    # 1. Simulate a source containing one invalid customer ID.
    billing = pd.DataFrame({
        "bill_id": ["B001", "B002"],
        "customer_id": ["C001", "   "],
        "created_at": [
            "2026-06-01",
            "2026-06-02",
        ],
        "updated_at": [
            "2026-06-05",
            "2026-06-06",
        ],
    })

    # 2. Expect the real validation function to reject the data.
    with pytest.raises(
        ValueError,
        match="Missing customer_id: 1 rows",
    ):
        pipeline.validate_billing_source(billing)


def test_validate_billing_source_updated_before_created():

    # 1. Simulate two billing records.
    billing = pd.DataFrame({
        "bill_id": ["B001", "B002"],
        "customer_id": ["C001", "C002"],
        "created_at": [
            "2026-06-01",
            "2026-06-08",
        ],
        "updated_at": [
            "2026-06-05",
            "2026-06-07",
        ],
    })

    # 2. Expect the production function to reject B002.
    with pytest.raises(
        ValueError,
        match="earlier than created_at",
    ):
        pipeline.validate_billing_source(billing)


def test_validate_billing_source_missing_required_column():

    # 1. Simulate a vendor CSV missing created_at.
    billing = pd.DataFrame({
        "bill_id": ["B001", "B002"],
        "customer_id": ["C001", "C002"],
        "updated_at": [
            "2026-06-05",
            "2026-06-06",
        ],
    })

    # 2. The production function must reject
    #    the missing required column.
    with pytest.raises(
        ValueError,
        match="Missing required column: created_at",
    ):
        pipeline.validate_billing_source(billing)


def test_incremental_load_no_new_records(tmp_path, monkeypatch):

    # 1. Create a temporary billing CSV.
    source_file = tmp_path / "test_billing.csv"

    billing = pd.DataFrame({
        "bill_id": ["B001", "B002", "B003"],
        "customer_id": ["C001", "C002", "C003"],
        "created_at": [
            "2026-06-01",
            "2026-06-02",
            "2026-06-03",
        ],
        "updated_at": [
            "2026-06-03",
            "2026-06-05",
            "2026-06-07",
        ],
    })

    billing.to_csv(source_file, index=False)

    # 2. Simulate a database engine.
    engine = MagicMock()

    # 3. Simulate the existing database watermark.
    fake_watermark = MagicMock(
        return_value=pd.Timestamp("2026-06-07")
    )

    monkeypatch.setattr(
        pipeline,
        "get_billing_watermark",
        fake_watermark,
    )

    # 4. Replace database-writing operations with mocks.
    fake_insert = MagicMock()

    monkeypatch.setattr(
        pd.DataFrame,
        "to_sql",
        fake_insert,
    )

    fake_update = MagicMock()

    monkeypatch.setattr(
        pipeline,
        "update_billing_watermark",
        fake_update,
    )

    # 5. Execute the actual Docker pipeline ingestion function.
    rows_loaded = pipeline.load_billing_raw_incremental(
        engine,
        source_file=source_file,
    )

    # 6. Verify expected behavior.
    assert rows_loaded == 0

    fake_watermark.assert_called_once()

    fake_insert.assert_not_called()

    fake_update.assert_not_called()


def test_incremental_load_new_records(tmp_path, monkeypatch):

    # 1. Create a temporary billing source CSV.
    source_file = tmp_path / "test_billing.csv"

    billing = pd.DataFrame({
        "bill_id": ["B001", "B002", "B003", "B004"],
        "customer_id": ["C001", "C002", "C003", "C004"],
        "created_at": [
            "2026-06-01",
            "2026-06-01",
            "2026-06-01",
            "2026-06-01",
        ],
        "updated_at": [
            "2026-06-05",
            "2026-06-07",
            "2026-06-08",
            "2026-06-09",
        ],
    })

    billing.to_csv(source_file, index=False)

    # 2. Create a fake database engine and connection.
    engine = MagicMock()

    connection = (
        engine.begin.return_value
        .__enter__.return_value
    )

    # 3. Simulate the existing watermark.
    fake_watermark = MagicMock(
        return_value=pd.Timestamp("2026-06-07")
    )

    monkeypatch.setattr(
        pipeline,
        "get_billing_watermark",
        fake_watermark,
    )

    # 4. Capture the records passed to to_sql().
    inserted_calls = []

    def fake_to_sql(self, **kwargs):
        inserted_calls.append({
            "data": self.copy(),
            "options": kwargs,
        })

    monkeypatch.setattr(
        pd.DataFrame,
        "to_sql",
        fake_to_sql,
    )

    # 5. Replace the watermark update with a mock.
    fake_update = MagicMock()

    monkeypatch.setattr(
        pipeline,
        "update_billing_watermark",
        fake_update,
    )

    # 6. Execute the real ingestion function.
    rows_loaded = pipeline.load_billing_raw_incremental(
        engine,
        source_file=source_file,
    )

    # 7. Verify the number of selected records.
    assert rows_loaded == 2

    # 8. Verify that an insertion was attempted once.
    assert len(inserted_calls) == 1

    inserted_data = inserted_calls[0]["data"]
    insert_options = inserted_calls[0]["options"]

    # 9. Verify only B003 and B004 were selected.
    assert inserted_data["bill_id"].tolist() == [
        "B003",
        "B004",
    ]

    # 10. Verify the source metadata.
    assert inserted_data["source_file_name"].tolist() == [
        "test_billing.csv",
        "test_billing.csv",
    ]

    # 11. Verify the intended RAW destination.
    assert insert_options["schema"] == "raw"
    assert insert_options["name"] == "billing_transactions"
    assert insert_options["if_exists"] == "append"

    # 12. Verify insertion uses the same connection.
    assert insert_options["con"] is connection

    # 13. Verify the watermark update.
    fake_update.assert_called_once_with(
        connection,
        pd.Timestamp("2026-06-09"),
    )


def test_incremental_load_insert_failure(tmp_path, monkeypatch):

    # 1. Create a temporary billing source CSV.
    source_file = tmp_path / "test_billing.csv"

    billing = pd.DataFrame({
        "bill_id": ["B005"],
        "customer_id": ["C005"],
        "created_at": ["2026-06-01"],
        "updated_at": ["2026-06-10"],
    })

    billing.to_csv(source_file, index=False)

    # 2. Create a fake database engine.
    engine = MagicMock()

    # 3. Simulate the current watermark.
    fake_watermark = MagicMock(
        return_value=pd.Timestamp("2026-06-07")
    )

    monkeypatch.setattr(
        pipeline,
        "get_billing_watermark",
        fake_watermark,
    )

    # 4. Simulate a failure during RAW insertion.
    def fake_to_sql(self, **kwargs):
        raise RuntimeError("Simulated RAW insert failure")

    monkeypatch.setattr(
        pd.DataFrame,
        "to_sql",
        fake_to_sql,
    )

    # 5. Replace the watermark update with a mock.
    fake_update = MagicMock()

    monkeypatch.setattr(
        pipeline,
        "update_billing_watermark",
        fake_update,
    )

    # 6. Run the production function and expect an error.
    with pytest.raises(
        RuntimeError,
        match="Simulated RAW insert failure",
    ):
        pipeline.load_billing_raw_incremental(
            engine,
            source_file=source_file,
        )

    # 7. Verify the watermark was retrieved.
    fake_watermark.assert_called_once()

    # 8. Verify the watermark update was NOT attempted.
    fake_update.assert_not_called()


def test_incremental_load_insert_failure(tmp_path, monkeypatch):

    # 1. Create a temporary billing source CSV.
    source_file = tmp_path / "test_billing.csv"

    billing = pd.DataFrame({
        "bill_id": ["B005"],
        "customer_id": ["C005"],
        "created_at": ["2026-06-01"],
        "updated_at": ["2026-06-10"],
    })

    billing.to_csv(source_file, index=False)

    # 2. Create a fake database engine.
    engine = MagicMock()

    # 3. Simulate the current watermark.
    fake_watermark = MagicMock(
        return_value=pd.Timestamp("2026-06-07")
    )

    monkeypatch.setattr(
        pipeline,
        "get_billing_watermark",
        fake_watermark,
    )

    # 4. Simulate a failure during RAW insertion.
    def fake_to_sql(self, **kwargs):
        raise RuntimeError("Simulated RAW insert failure")

    monkeypatch.setattr(
        pd.DataFrame,
        "to_sql",
        fake_to_sql,
    )

    # 5. Replace the watermark update with a mock.
    fake_update = MagicMock()

    monkeypatch.setattr(
        pipeline,
        "update_billing_watermark",
        fake_update,
    )

    # 6. Run the production function and expect an error.
    with pytest.raises(
        RuntimeError,
        match="Simulated RAW insert failure",
    ):
        pipeline.load_billing_raw_incremental(
            engine,
            source_file=source_file,
        )

    # 7. Verify the watermark was retrieved.
    fake_watermark.assert_called_once()

    # 8. Verify the watermark update was NOT attempted.
    fake_update.assert_not_called()


def test_incremental_load_watermark_update_failure(
    tmp_path, monkeypatch
):

    # 1. Create temporary billing source data.
    source_file = tmp_path / "test_billing.csv"

    billing = pd.DataFrame({
        "bill_id": ["B005"],
        "customer_id": ["C005"],
        "created_at": ["2026-06-01"],
        "updated_at": ["2026-06-10"],
    })

    billing.to_csv(source_file, index=False)

    # 2. Create fake database engine and connection.
    engine = MagicMock()

    connection = (
        engine.begin.return_value
        .__enter__.return_value
    )

    # 3. Simulate existing watermark.
    fake_watermark = MagicMock(
        return_value=pd.Timestamp("2026-06-07")
    )

    monkeypatch.setattr(
        pipeline,
        "get_billing_watermark",
        fake_watermark,
    )

    # 4. Simulate successful RAW insertion.
    fake_insert = MagicMock()

    monkeypatch.setattr(
        pd.DataFrame,
        "to_sql",
        fake_insert,
    )

    # 5. Simulate failure during watermark update.
    fake_update = MagicMock(
        side_effect=RuntimeError(
            "Simulated watermark update failure"
        )
    )

    monkeypatch.setattr(
        pipeline,
        "update_billing_watermark",
        fake_update,
    )

    # 6. Execute production function; expect failure.
    with pytest.raises(
        RuntimeError,
        match="Simulated watermark update failure",
    ):
        pipeline.load_billing_raw_incremental(
            engine,
            source_file=source_file,
        )

    # 7. RAW insertion was attempted once.
    fake_insert.assert_called_once()

    # 8. Watermark update was attempted with correct values.
    fake_update.assert_called_once_with(
        connection,
        pd.Timestamp("2026-06-10"),
    )


def test_incremental_load_watermark_update_failure(
    tmp_path, monkeypatch
):

    # 1. Create temporary billing source data.
    source_file = tmp_path / "test_billing.csv"

    billing = pd.DataFrame({
        "bill_id": ["B005"],
        "customer_id": ["C005"],
        "created_at": ["2026-06-01"],
        "updated_at": ["2026-06-10"],
    })

    billing.to_csv(source_file, index=False)

    # 2. Create fake database engine and connection.
    engine = MagicMock()

    connection = (
        engine.begin.return_value
        .__enter__.return_value
    )

    # 3. Simulate existing watermark.
    fake_watermark = MagicMock(
        return_value=pd.Timestamp("2026-06-07")
    )

    monkeypatch.setattr(
        pipeline,
        "get_billing_watermark",
        fake_watermark,
    )

    # 4. Simulate successful RAW insertion.
    fake_insert = MagicMock()

    monkeypatch.setattr(
        pd.DataFrame,
        "to_sql",
        fake_insert,
    )

    # 5. Simulate failure during watermark update.
    fake_update = MagicMock(
        side_effect=RuntimeError(
            "Simulated watermark update failure"
        )
    )

    monkeypatch.setattr(
        pipeline,
        "update_billing_watermark",
        fake_update,
    )

    # 6. Execute production function; expect failure.
    with pytest.raises(
        RuntimeError,
        match="Simulated watermark update failure",
    ):
        pipeline.load_billing_raw_incremental(
            engine,
            source_file=source_file,
        )

    # 7. RAW insertion was attempted once.
    fake_insert.assert_called_once()

    # 8. Watermark update was attempted with correct values.
    fake_update.assert_called_once_with(
        connection,
        pd.Timestamp("2026-06-10"),
    )
