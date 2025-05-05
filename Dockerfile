# Start from the official Airflow image
FROM apache/airflow:2.6.3-python3.9

# Switch to root to install system dependencies
USER root

# Set working directory
WORKDIR /app

# Install Java and required tools
RUN apt-get update && \
    apt-get install -y default-jdk wget curl unzip && \
    apt-get clean

# Dynamically set JAVA_HOME
RUN JAVA_PATH=$(readlink -f $(which java)) && \
    JAVA_HOME=$(dirname $(dirname "$JAVA_PATH")) && \
    echo "export JAVA_HOME=$JAVA_HOME" >> /etc/profile && \
    echo "export PATH=\$JAVA_HOME/bin:\$PATH" >> /etc/profile && \
    echo "$JAVA_HOME" > /java_home

RUN export JAVA_HOME=$(cat /java_home) && \
    echo "JAVA_HOME=$JAVA_HOME"

ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
ENV PATH=$JAVA_HOME/bin:$PATH

# Create necessary directories
RUN mkdir -p /app/scripts /opt/spark/jars

# Switch back to airflow user
USER airflow

# Copy and install Python dependencies
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
