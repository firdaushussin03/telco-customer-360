
import pendulum
from airflow.sdk import dag, task


@dag(
    dag_id="telco_airflow_learning",
    schedule=None,
    start_date=pendulum.datetime(2026, 11, 1, tz="Asia/Kuala_Lumpur"),
    catchup=False,
    tags=["telco", "learning"],
)
def telco_airflow_learning():

    @task
    def extract_example_billing():
        # Example data, NOT from our real Telco database
        return [
            {"bill_id": "B001", "payment_status": "Paid"},
            {"bill_id": "B002", "payment_status": "Pending"},
            {"bill_id": "B003", "payment_status": "Paid"},
        ]

    @task
    def count_paid_bills(bills):
        paid_count = sum(
            bill["payment_status"] == "Paid"
            for bill in bills
        )

        print(f"Number of paid bills: {paid_count}")
        return paid_count

    # Define the task dependency
    count_paid_bills(extract_example_billing())


# Instantiate the DAG so Airflow can discover it
telco_airflow_learning()
