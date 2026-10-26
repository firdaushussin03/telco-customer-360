
# ============================================================
# TELCO CUSTOMER 360 - SOURCE FILE VALIDATION TESTS
# File: tests/test_source_files.py
# ============================================================

import importlib.util
import pytest
from pathlib import Path


# Locate the actual initialization script.
SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "58_initialize_if_needed.py"
)

# Import the script without executing main().
spec = importlib.util.spec_from_file_location(
    "telco_initializer", SCRIPT_PATH
)

initializer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(initializer)


def test_verify_source_files_all_present(tmp_path, monkeypatch):

    # Create a temporary folder structure.
    fake_src = tmp_path / "src"
    fake_src.mkdir()

    raw_dir = tmp_path / "data" / "raw"
    raw_dir.mkdir(parents=True)

    # Create five empty placeholder files.
    required_files = [
        "Telco_customer_churn_demographics.xlsx",
        "Telco_customer_churn_location.xlsx",
        "Telco_customer_churn_population.xlsx",
        "Telco_customer_churn_services.xlsx",
        "Telco_customer_churn_status.xlsx",
    ]

    for filename in required_files:
        (raw_dir / filename).touch()

    # Make the real function use our temporary folder.
    monkeypatch.setattr(
        initializer,
        "__file__",
        str(fake_src / "58_initialize_if_needed.py"),
    )

    # Call the actual production function.
    # The test passes if no exception is raised.
    initializer.verify_source_files()
    

def test_verify_source_files_missing_one(tmp_path, monkeypatch):

    # Create temporary folders.
    fake_src = tmp_path / "src"
    fake_src.mkdir()

    raw_dir = tmp_path / "data" / "raw"
    raw_dir.mkdir(parents=True)

    # Create only FOUR placeholder Excel files.
    present_files = [
        "Telco_customer_churn_demographics.xlsx",
        "Telco_customer_churn_location.xlsx",
        "Telco_customer_churn_population.xlsx",
        "Telco_customer_churn_services.xlsx",
    ]

    for filename in present_files:
        (raw_dir / filename).touch()

    # Redirect script 58 to our temporary folder.
    monkeypatch.setattr(
        initializer,
        "__file__",
        str(fake_src / "58_initialize_if_needed.py"),
    )

    # Check that the expected error occurs.
    with pytest.raises(
        FileNotFoundError,
        match="Telco_customer_churn_status",
    ):
        initializer.verify_source_files()

