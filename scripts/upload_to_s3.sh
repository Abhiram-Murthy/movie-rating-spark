#!/bin/bash
# Usage: ./scripts/upload_to_s3.sh <bucket-name> [region]
BUCKET=$1; REGION=${2:-ap-south-1}
aws s3 mb s3://$BUCKET --region $REGION 2>/dev/null || true
aws s3 cp data/ratings.csv s3://$BUCKET/raw/ratings.csv
aws s3 cp data/movies.csv  s3://$BUCKET/raw/movies.csv
aws s3 ls s3://$BUCKET/raw/
