from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import json
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "scripts"))

from scraper import scrape_imdb_top_250
from kafka_producer import publish_to_kafka
from db_writer import write_to_postgres
from metrics import push_scrape_metrics

default_args = {
    'retries': 1,
}

with DAG("scrape_imdb_data_dag",
         schedule_interval="*/30 * * * *",
         start_date=datetime(2024, 1, 1),
         catchup=False,
         default_args=default_args) as dag:

    def scrape_task():
        data = scrape_imdb_top_250()
        os.makedirs("/opt/airflow/data", exist_ok=True)
        with open("/opt/airflow/data/top_250.json", "w") as f:
            json.dump(data, f)
        return data

    scrape_movies = PythonOperator(
        task_id="scrape_movies_task",
        python_callable=scrape_task
    )

    def save_to_postgres_task(**context):
        data = context['ti'].xcom_pull(task_ids='scrape_movies_task')
        write_to_postgres(data)

    save_to_postgres = PythonOperator(
        task_id="save_to_postgres_task",
        python_callable=save_to_postgres_task,
        provide_context=True
    )

    def send_to_kafka_task(**context):
        data = context['ti'].xcom_pull(task_ids='scrape_movies_task')
        publish_to_kafka(data)

    send_to_kafka = PythonOperator(
        task_id="publish_to_kafka_task",
        python_callable=send_to_kafka_task,
        provide_context=True
    )

    def push_metrics_task(**context):
        data = context['ti'].xcom_pull(task_ids='scrape_movies_task')
        push_scrape_metrics(len(data))

    push_metrics = PythonOperator(
        task_id="push_scrape_metrics_task",
        python_callable=push_metrics_task,
        provide_context=True
    )

    scrape_movies >> [save_to_postgres, send_to_kafka] >> push_metrics
