#!/bin/bash
# Usage: ./scripts/run_on_ec2.sh <bucket-name>
# EC2 must have an IAM role with S3 read/write on the bucket (no keys in code!).
BUCKET=$1
spark-submit \
  --master "local[*]" \
  --driver-memory 6g \
  --packages org.apache.hadoop:hadoop-aws:3.3.4,com.amazonaws:aws-java-sdk-bundle:1.12.262 \
  --conf spark.hadoop.fs.s3a.aws.credentials.provider=com.amazonaws.auth.InstanceProfileCredentialsProvider \
  src/movie_rating_analysis.py \
  --input  s3a://$BUCKET/raw \
  --output s3a://$BUCKET/results \
  --als
