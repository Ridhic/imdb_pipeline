from kafka import KafkaProducer
import json

def publish_to_kafka(data, topic='imdb_movies_stream'):
    producer = KafkaProducer(
        bootstrap_servers='kafka:9092',
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )

    for record in data:
        producer.send(topic, value=record)

    producer.flush()
