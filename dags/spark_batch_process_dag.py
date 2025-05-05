from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
from pyspark.sql import SparkSession
from pyspark.sql.functions import col
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway
from elasticsearch import Elasticsearch
import json

# Function to create a Spark session
def create_spark_session():
    return SparkSession.builder \
        .appName("BatchProcessingIMDB") \
        .config("spark.jars", "/opt/spark/jars/*") \
        .getOrCreate()

# Function to read data from PostgreSQL
def read_from_postgres(**kwargs):
    spark = create_spark_session()
    df = spark.read \
        .format("jdbc") \
        .option("url", "jdbc:postgresql://postgres:5432/imdb") \
        .option("dbtable", "imdb_movies") \
        .option("user", "postgres") \
        .option("password", "postgres") \
        .option("driver", "org.postgresql.Driver") \
        .load()
    
    df.createOrReplaceTempView("imdb_movies")
    df.write.mode("overwrite").parquet("/tmp/imdb_batch_data.parquet")

# Function to perform data transformations
def transform_data(**kwargs):
    spark = create_spark_session()
    df = spark.read.parquet("/tmp/imdb_batch_data.parquet")

    df_transformed = df.withColumn("decade", (col("year").cast("int") / 10).cast("int") * 10)
    
    df_transformed.write.mode("overwrite").parquet("/tmp/imdb_transformed.parquet")

# ✅ Function to run manual quality checks
def run_quality_checks(**kwargs):
    spark = create_spark_session()
    df = spark.read.parquet("/tmp/imdb_transformed.parquet")

    errors = []

    # Title: not null or empty
    null_title_count = df.filter((col("title").isNull()) | (col("title") == "")).count()
    if null_title_count > 0:
        errors.append(f"{null_title_count} rows have null or empty titles.")

    # Rating: not null and in range
    invalid_rating_count = df.filter((col("rating").isNull()) | (col("rating") < 0) | (col("rating") > 10)).count()
    if invalid_rating_count > 0:
        errors.append(f"{invalid_rating_count} rows have invalid ratings.")

    # Year: not null and in range
    invalid_year_count = df.filter((col("year").isNull()) | (col("year") < 1900) | (col("year") > 2025)).count()
    if invalid_year_count > 0:
        errors.append(f"{invalid_year_count} rows have invalid years.")

    # Vote count: not null and non-negative
    invalid_vote_count = df.filter((col("vote_count").isNull()) | (col("vote_count") < 0)).count()
    if invalid_vote_count > 0:
        errors.append(f"{invalid_vote_count} rows have invalid vote counts.")

    # Image: if not null, must start with http/https
    invalid_image_count = df.filter((~col("image").startswith("http")) & (col("image").isNotNull())).count()
    if invalid_image_count > 0:
        errors.append(f"{invalid_image_count} rows have invalid image URLs.")

    # Plot: if present, should have at least 10 characters
    invalid_plot_count = df.filter((col("plot").isNotNull()) & (col("plot").rlike("^.{0,9}$"))).count()
    if invalid_plot_count > 0:
        errors.append(f"{invalid_plot_count} rows have very short plot descriptions.")

    # Raise error if any checks failed
    if errors:
        raise ValueError("Data quality check failed:\n" + "\n".join(errors))
    
    print("All data quality checks passed.")

# Function to write data to Elasticsearch
def write_to_elasticsearch(**kwargs):
    es = Elasticsearch("http://elasticsearch:9200")
    spark = create_spark_session()
    df = spark.read.parquet("/tmp/imdb_transformed.parquet")
    rows = df.toJSON().collect()
    
    for row in rows:
        doc = json.loads(row)
        es.index(index="imdb_batch", body=doc)

# Function to push metrics to Prometheus
def push_metrics(**kwargs):
    registry = CollectorRegistry()
    batch_success_gauge = Gauge('spark_batch_success', 'Batch Process Success', registry=registry)
    batch_success_gauge.set(1)

    es = Elasticsearch("http://elasticsearch:9200")
    try:
        stream_count = es.count(index="imdb_stream")['count']
    except Exception as e:
        print(f"Error fetching stream metrics: {e}")
        stream_count = 0

    stream_valid_gauge = Gauge('stream_valid_rows_total', 'Total valid rows processed by stream job', registry=registry)
    stream_valid_gauge.set(stream_count)

    push_to_gateway('pushgateway:9091', job='batch_and_stream_metrics_collector', registry=registry)

# Define the DAG and tasks
with DAG(
    'spark_batch_process_dag',
    schedule_interval='@daily',
    start_date=datetime(2024, 1, 1),
    catchup=False
) as dag:

    read_data = PythonOperator(
        task_id='consume_from_source_task',
        python_callable=read_from_postgres
    )

    transform = PythonOperator(
        task_id='transform_with_pyspark_task',
        python_callable=transform_data
    )

    quality = PythonOperator(
        task_id='run_data_quality_checks_task',
        python_callable=run_quality_checks
    )

    write_es = PythonOperator(
        task_id='write_to_elasticsearch_task',
        python_callable=write_to_elasticsearch
    )

    metrics = PythonOperator(
        task_id='push_metrics_to_prometheus',
        python_callable=push_metrics
    )

    # Task dependencies
    read_data >> transform >> quality >> write_es >> metrics
