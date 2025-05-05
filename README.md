# IMDB Data Pipeline using Apache Spark, Kafka, PostgreSQL, and Elasticsearch

This project implements a robust, scalable data pipeline for processing and analyzing IMDB movie data using both batch and stream processing paradigms. The system leverages Apache Spark, Kafka, PostgreSQL, Elasticsearch, and Prometheus with Grafana for monitoring.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Technology Stack](#technology-stack)
- [Data Schema](#data-schema)
- [Batch Processing Workflow](#batch-processing-workflow)
- [Streaming Processing Workflow](#streaming-processing-workflow)
- [Data Quality Validation](#data-quality-validation)
- [Monitoring and Metrics](#monitoring-and-metrics)
- [Project Structure](#project-structure)
- [Setup and Execution](#setup-and-execution)
- [Future Enhancements](#future-enhancements)
- [License](#license)

---

## Architecture Overview

- **Batch Workflow (Daily)**:
  - Reads data from a PostgreSQL table.
  - Performs validation and transformation using Apache Spark.
  - Writes processed records to Elasticsearch.
  - Pushes metrics to Prometheus Pushgateway for Grafana visualization.

- **Stream Workflow (Real-time)**:
  - Ingests JSON movie records from Kafka.
  - Applies schema validation and data cleaning in Spark Structured Streaming.
  - Sends valid records to Elasticsearch and logs metrics to Prometheus.

---

## Technology Stack

| Component      | Technology                     |
|----------------|--------------------------------|
| Batch Engine   | Apache Spark (PySpark)         |
| Stream Engine  | Spark Structured Streaming     |
| Messaging      | Apache Kafka                   |
| Database       | PostgreSQL                     |
| Search Engine  | Elasticsearch                  |
| Monitoring     | Prometheus + Grafana           |
| Orchestration  | Apache Airflow                 |
| Language       | Python                         |

---

## Data Schema

Each record contains the following fields:

| Field       | Type    | Description                  |
|-------------|---------|------------------------------|
| `title`     | String  | Movie title                  |
| `image`     | String  | URL to the movie poster      |
| `year`      | Integer | Year of release              |
| `rating`    | Float   | IMDb rating (0.0 to 10.0)     |
| `vote_count`| Integer | Number of votes              |
| `plot`      | String  | Short plot summary           |

---

## Batch Processing Workflow

- **Source**: PostgreSQL
- **Transformations**:
  - Null handling and basic validation
  - Optional computation of derived fields (e.g., `decade`)
- **Sink**: Elasticsearch index (`imdb_batch`)
- **Metrics**:
  - `spark_batch_success`: Indicates successful execution
  - `stream_valid_rows_total`: Snapshot of valid rows in stream index

Scheduled using Apache Airflow with daily frequency.

---

## Streaming Processing Workflow

- **Source**: Apache Kafka (`imdb_movies_stream` topic)
- **Operations**:
  - Schema enforcement and parsing
  - Validation: rating (1–10), non-null critical fields
  - Null handling for optional fields
- **Sink**: Elasticsearch index (`imdb_stream`)
- **Metrics**:
  - `valid_rows_processed`: Valid rows written to Elasticsearch
  - `invalid_rows_processed`: Invalid rows discarded

---

## Data Quality Validation

### Criteria Applied:
- `title` must be non-null
- `year`, `rating`, `vote_count`, `plot`, and `image` must be present
- `rating` must be between 1.0 and 10.0

Invalid records are filtered out during streaming and counted for monitoring.

---

## Monitoring and Metrics

Prometheus metrics are pushed via **Pushgateway**, and visualized using **Grafana dashboards**.

### Key Metrics:
| Metric Name             | Description                            |
|-------------------------|----------------------------------------|
| `valid_rows_processed`  | Number of valid stream records         |
| `invalid_rows_processed`| Number of invalid stream records       |
| `spark_batch_success`   | Binary flag for batch success          |
| `stream_valid_rows_total` | Real-time count of stream index data |

Grafana is used to:
- Monitor streaming throughput
- Visualize valid/invalid record trends
- Observe system performance and batch DAG status