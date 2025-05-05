from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json
from pyspark.sql.types import StructType, StringType, FloatType, IntegerType
from prometheus_client import Counter, CollectorRegistry, push_to_gateway

# Prometheus Counters
registry = CollectorRegistry()
valid_rows_counter = Counter('valid_rows_processed', 'Number of valid rows processed', registry=registry)
invalid_rows_counter = Counter('invalid_rows_processed', 'Number of invalid rows processed', registry=registry)

def main():
    spark = SparkSession.builder \
        .appName("SparkStructuredStreaming") \
        .config("spark.es.nodes", "elasticsearch:9200") \
        .config("spark.es.resource", "imdb_stream/_doc") \
        .getOrCreate()

    # Define Kafka message schema
    schema = StructType() \
        .add("title", StringType()) \
        .add("image", StringType()) \
        .add("year", IntegerType()) \
        .add("rating", FloatType()) \
        .add("vote_count", IntegerType()) \
        .add("plot", StringType())

    # Read Kafka stream
    kafka_stream_df = spark.readStream.format("kafka") \
        .option("kafka.bootstrap.servers", "kafka:9092") \
        .option("subscribe", "imdb_movies_stream") \
        .load()

    # Parse the Kafka message value
    parsed_df = kafka_stream_df.selectExpr("CAST(value AS STRING)") \
        .select(from_json("value", schema).alias("data")) \
        .select("data.*")

    def process_batch(batch_df, batch_id):
        if batch_df.isEmpty():
            return

        # Handle missing values
        cleaned_df = batch_df.fillna({'rating': 0.0, 'title': 'Unknown'})

        df_with_decade = cleaned_df.withColumn("decade", (col("year").cast("int") / 10).cast("int") * 10)

        # Sort by rating
        sorted_df = df_with_decade.orderBy(col("rating").desc())

        # Filter valid/invalid rows (consider year)
        valid_data_df = sorted_df.filter(
            (col("title").isNotNull()) & (col("title") != "") &
            (col("year").isNotNull()) & (col("year") >= 1900) & (col("year") <= 2025) &
            (col("rating").isNotNull()) & (col("rating") >= 1) & (col("rating") <= 10) &
            (col("vote_count").isNotNull()) & (col("vote_count") >= 0) &
            (col("plot").isNotNull()) & (col("plot") != "") &
            (col("image").isNotNull()) & (col("image") != "")
        )

        invalid_data_df = sorted_df.exceptAll(valid_data_df)

        # Update Prometheus metrics
        valid_count = valid_data_df.count()
        invalid_count = invalid_data_df.count()

        valid_rows_counter.inc(valid_count)
        invalid_rows_counter.inc(invalid_count)

        push_to_gateway('pushgateway:9091', job='spark_stream_job', registry=registry)

        # Write valid rows to Elasticsearch
        try:
            valid_data_df.write \
                .format("org.elasticsearch.spark.sql") \
                .option("es.resource", "imdb_stream/_doc") \
                .option("es.nodes", "elasticsearch:9200") \
                .mode("append") \
                .save()
        except Exception as e:
            print(f"Error writing to Elasticsearch: {e}")

        # Optionally log bad data
        if invalid_count > 0:
            print(f"Invalid rows: {invalid_count}")
            invalid_data_df.show(truncate=False)

    parsed_df.printSchema()

    # Start streaming
    parsed_df.writeStream \
        .foreachBatch(process_batch) \
        .outputMode("append") \
        .start() \
        .awaitTermination()

if __name__ == "__main__":
    main()
