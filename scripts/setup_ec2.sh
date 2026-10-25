#!/bin/bash
# Run on a fresh EC2 instance (Ubuntu 22.04/24.04, t3.large or bigger recommended).
set -e
sudo apt-get update -y
sudo apt-get install -y openjdk-17-jdk python3-pip python3-setuptools unzip curl awscli

SPARK_VERSION=3.5.1
curl -O https://archive.apache.org/dist/spark/spark-${SPARK_VERSION}/spark-${SPARK_VERSION}-bin-hadoop3.tgz
tar -xzf spark-${SPARK_VERSION}-bin-hadoop3.tgz
sudo mv spark-${SPARK_VERSION}-bin-hadoop3 /opt/spark

cat >> ~/.bashrc << 'RC'
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
export SPARK_HOME=/opt/spark
export PATH=$PATH:$SPARK_HOME/bin
RC
echo "Done. Run: source ~/.bashrc && spark-submit --version"
