import pandas as pd
from pathlib import Path

# ============================================================
# TELCO CUSTOMER 360 - DATA UNDERSTANDING
# File: 01_data_understanding.py
# Purpose:
#   - Inspect the five IBM Telco source files
#   - Check data types, missing values, blanks, duplicates
#   - Validate candidate primary keys
#   - Validate relationships between the source datasets
# ============================================================

BASE_DIR = Path(
    r"C:\Users\mohd5\Documents\telco-customer-360\data\raw"
)

FILES = {
    "demographics": {
        "file": "Telco_customer_churn_demographics.xlsx",
        "primary_key": "Customer ID",
        "customer_key": "Customer ID",
    },
    "location": {
        "file": "Telco_customer_churn_location.xlsx",
        "primary_key": "Location ID",
        "customer_key": "Customer ID",
    },
    "population": {
        "file": "Telco_customer_churn_population.xlsx",
        "primary_key": "Zip Code",
        "customer_key": None,
    },
    "services": {
        "file": "Telco_customer_churn_services.xlsx",
        "primary_key": "Service ID",
        "customer_key": "Customer ID",
    },
    "status": {
        "file": "Telco_customer_churn_status.xlsx",
        "primary_key": "Status ID",
        "customer_key": "Customer ID",
    },
}


def inspect_dataset(name, df, primary_key, customer_key=None):
    """Print a consistent data-understanding report for one dataset."""

    print("\n" + "=" * 70)
    print(f"DATASET: {name.upper()}")
    print("=" * 70)

    # Basic structure
    print("\nShape:")
    print(df.shape)

    print("\nColumns:")
    print(df.columns.tolist())

    print("\nFirst 5 rows:")
    print(df.head())

    print("\nData Types:")
    print(df.dtypes)

    # Duplicate checks
    print("\nDuplicate Rows:")
    print(df.duplicated().sum())

    print(f"\nDuplicate {primary_key} Values:")
    print(df[primary_key].duplicated().sum())

    # Missing values
    print("\nMissing Values:")
    print(df.isnull().sum())

    # Blank / whitespace-only strings
    print("\nBlank / White Space Values:")
    text_df = df.select_dtypes(include=["object", "string"])

    if text_df.empty:
        print("No text columns.")
    else:
        print(
            text_df.apply(
                lambda col: col.fillna("").astype(str).str.strip().eq("")
            ).sum()
        )

    # Primary key validation
    print(f"\nPrimary Key Check - {primary_key}:")
    print(f"Number of rows: {len(df)}")
    print(f"Unique {primary_key}: {df[primary_key].nunique()}")
    print(f"Duplicate {primary_key}: {df[primary_key].duplicated().sum()}")
    print(f"Missing {primary_key}: {df[primary_key].isnull().sum()}")

    if (
        df[primary_key].nunique() == len(df)
        and df[primary_key].isnull().sum() == 0
    ):
        print(f"Result: {primary_key} is unique and has no missing values.")
    else:
        print(f"Result: {primary_key} needs further investigation.")

    # Customer ID validation for customer-level tables
    if customer_key and customer_key != primary_key:
        print(f"\nCustomer Key Check - {customer_key}:")
        print(f"Unique {customer_key}: {df[customer_key].nunique()}")
        print(f"Duplicate {customer_key}: {df[customer_key].duplicated().sum()}")
        print(f"Missing {customer_key}: {df[customer_key].isnull().sum()}")


def check_relationships(dataframes):
    """Validate important relationships between the five source datasets."""

    print("\n" + "=" * 70)
    print("RELATIONSHIP VALIDATION")
    print("=" * 70)

    demographics = dataframes["demographics"]
    location = dataframes["location"]
    population = dataframes["population"]
    services = dataframes["services"]
    status = dataframes["status"]

    # --------------------------------------------------------
    # Check whether the customer-level tables contain the same
    # Customer IDs as demographics.
    # --------------------------------------------------------
    demographic_customers = set(demographics["Customer ID"])

    for table_name, df in {
        "location": location,
        "services": services,
        "status": status,
    }.items():
        table_customers = set(df["Customer ID"])

        missing_from_table = demographic_customers - table_customers
        extra_in_table = table_customers - demographic_customers

        print(f"\nDemographics -> {table_name.title()}")
        print(f"Customers missing from {table_name}: {len(missing_from_table)}")
        print(f"Extra customers in {table_name}: {len(extra_in_table)}")

        if not missing_from_table and not extra_in_table:
            print("Result: Customer IDs match demographics.")
        else:
            print("Result: Customer ID relationship needs investigation.")

    # --------------------------------------------------------
    # Check Location -> Population using Zip Code
    # --------------------------------------------------------
    population_zip_codes = set(population["Zip Code"])
    location_zip_codes = set(location["Zip Code"])

    missing_population_zip_codes = location_zip_codes - population_zip_codes

    print("\nPopulation -> Location")
    print(f"Unique population Zip Codes: {population['Zip Code'].nunique()}")
    print(f"Unique location Zip Codes: {location['Zip Code'].nunique()}")
    print(
        "Location Zip Codes missing from population: "
        f"{len(missing_population_zip_codes)}"
    )

    if not missing_population_zip_codes:
        print("Result: Every location Zip Code exists in population.")
    else:
        print("Result: Some location Zip Codes do not exist in population.")

    # --------------------------------------------------------
    # Relationship cardinality checks
    # --------------------------------------------------------
    print("\nRelationship Cardinality Summary:")

    print(
        "demographics -> location: "
        + (
            "1:1"
            if location["Customer ID"].is_unique
            else "1:M or needs investigation"
        )
    )

    print(
        "demographics -> services: "
        + (
            "1:1"
            if services["Customer ID"].is_unique
            else "1:M or needs investigation"
        )
    )

    print(
        "demographics -> status: "
        + (
            "1:1"
            if status["Customer ID"].is_unique
            else "1:M or needs investigation"
        )
    )

    zip_counts = location["Zip Code"].value_counts()
    if (zip_counts > 1).any():
        print("population -> location: 1:M")
    else:
        print("population -> location: 1:1")


def main():
    dataframes = {}

    # Load and inspect all source files
    for name, config in FILES.items():
        file_path = BASE_DIR / config["file"]

        if not file_path.exists():
            print(f"\nERROR: File not found: {file_path}")
            continue

        df = pd.read_excel(file_path)
        dataframes[name] = df

        inspect_dataset(
            name=name,
            df=df,
            primary_key=config["primary_key"],
            customer_key=config["customer_key"],
        )

    # Only run relationship checks if all five files loaded
    if len(dataframes) == len(FILES):
        check_relationships(dataframes)
    else:
        print(
            "\nRelationship checks were skipped because one or more "
            "source files could not be loaded."
        )


if __name__ == "__main__":
    main()
