import os
import yaml
import requests
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from google.cloud import bigquery

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/opt/airflow/config/gcp-credentials.json"
client = bigquery.Client(project="oss-pulse-509119")

default_args = {
    "owner": "aishwarya.bokil",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "start_date": datetime(2026, 9, 19),
}

def load_repos():
    with open("/opt/airflow/config/repos.yaml", "r") as f:
        config = yaml.safe_load(f)
    return config["repos"]

def fetch_repo_data(repo_name):
    token = os.getenv("GITHUB_TOKEN")
    headers = {"Authorization": f"Bearer {token}"}
    
    url = f"https://api.github.com/repos/{repo_name}"
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    
    return response.json()

def create_table_if_not_exists():
    schema = [
        bigquery.SchemaField("repo_name", "STRING"),
        bigquery.SchemaField("stars", "INTEGER"),
        bigquery.SchemaField("forks", "INTEGER"),
        bigquery.SchemaField("open_issues", "INTEGER"),
        bigquery.SchemaField("watchers", "INTEGER"),
        bigquery.SchemaField("ingested_at", "TIMESTAMP"),
    ]
    
    table_id = "oss-pulse-509119.oss_pulse_raw.github_repos"
    table = bigquery.Table(table_id, schema=schema)
    client.create_table(table, exists_ok=True)

def load_to_bigquery(rows):
    table_id = "oss-pulse-509119.oss_pulse_raw.github_repos"

    # Batch load job rather than streaming insert_rows_json, which the BigQuery free tier rejects
    job = client.load_table_from_json(rows, table_id)
    job.result()

def run_ingestion():
    repos = load_repos()
    create_table_if_not_exists()

    # Fetch every repo first and load them as a single job, so a run either lands
    # all repos or none — no partial days, no repos re-loaded on retry.
    ingested_at = datetime.utcnow().isoformat()
    rows = []
    for repo_name in repos:
        data = fetch_repo_data(repo_name)
        rows.append({
            "repo_name": repo_name,
            "stars": data.get("stargazers_count"),
            "forks": data.get("forks_count"),
            "open_issues": data.get("open_issues_count"),
            "watchers": data.get("watchers_count"),
            "ingested_at": ingested_at,
        })

    load_to_bigquery(rows)


with DAG(
    dag_id="github_ingest",
    default_args=default_args,
    schedule="@daily",
    catchup=False,
    description="Ingest GitHub repo health metrics into BigQuery",
) as dag:
    ingest_task = PythonOperator(
        task_id="run_ingestion",
        python_callable=run_ingestion,
    )
