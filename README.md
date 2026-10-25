# Movie Rating Analysis using Apache Spark

| | |
|---|---|
| **Big Data Framework** | Apache Spark (PySpark, Spark SQL, MLlib) |
| **Cloud Provider & Service** | AWS S3 (storage) + EC2 (compute) |
| **Dataset** | MovieLens (GroupLens) – `ratings.csv`, `movies.csv` |

## 1. Problem Statement
Streaming/rating platforms generate millions of ratings. This project uses Spark on AWS to process
them at scale and answer: which movies and genres are rated best, how do ratings change over time,
how do users behave, and can we recommend movies to users?

## 2. Architecture
```
MovieLens CSV ──► S3 (raw/) ──► EC2 (Spark 3.5 + PySpark) ──► S3 (results/ : Parquet + CSV)
                                        │                              │
                                  ALS recommender              make_charts.py → report charts
```

## 3. Project Structure
```
src/movie_rating_analysis.py   main Spark job (cleaning, analytics, ALS)
src/generate_sample_data.py    tiny synthetic dataset for local testing
src/make_charts.py             charts from CSV results
scripts/setup_ec2.sh           install Java + Spark on EC2
scripts/upload_to_s3.sh        create bucket, upload data
scripts/run_on_ec2.sh          spark-submit with S3 (s3a) access
```

## 4. Analyses Performed
1. Dataset summary (ratings, users, movies, mean, std-dev)
2. Rating distribution
3. Top / bottom / most-rated movies (min-ratings threshold)
4. IMDb-style Bayesian weighted rating (fixes small-sample bias)
5. Genre analysis (explode multi-genre column)
6. Yearly rating trend
7. User activity and segmentation (Light / Regular / Heavy)
8. ALS collaborative-filtering recommender (RMSE + top-5 recs per user)

## 5. Run Locally (test first)
```bash
pip install -r requirements.txt          # needs Java 11/17 (setuptools is required on Python 3.12 for MLlib)
python src/generate_sample_data.py       # or put MovieLens CSVs in data/
spark-submit src/movie_rating_analysis.py --input data --output output --min-ratings 20 --als
python src/make_charts.py output
```
Real data: https://grouplens.org/datasets/movielens/ (`ml-latest-small` for testing, `ml-25m` for big-data scale).

## 6. Run on AWS (S3 + EC2)
1. **S3:** create a bucket, e.g. `movie-rating-<yourname>`. Upload data:
   `./scripts/upload_to_s3.sh movie-rating-<yourname> ap-south-1`
2. **IAM:** create a role with `AmazonS3FullAccess` (or a bucket-scoped policy) and attach it to the EC2 instance.
   Do not hard-code access keys.
3. **EC2:** launch Ubuntu 22.04, `t3.large` (2 vCPU / 8 GB) or bigger, 20 GB disk,
   allow SSH (port 22) from your IP; optional port 4040 for the Spark UI.
4. **Setup:** SSH in, copy this project over (`scp -r` or `git clone`), then
   `bash scripts/setup_ec2.sh && source ~/.bashrc`
5. **Run:** `./scripts/run_on_ec2.sh movie-rating-<yourname>`
6. **Results:** in `s3://movie-rating-<yourname>/results/`. Download with
   `aws s3 sync s3://movie-rating-<yourname>/results ./output` and run `make_charts.py`.
7. **Stop/terminate the EC2 instance** when done to avoid charges.

## 7. Suggested Report Outline
Abstract · Introduction · Problem statement · Dataset · Architecture (diagram above) · Methodology
(cleaning → analytics → ALS) · Implementation on AWS (screenshots: S3 bucket, EC2 instance, Spark UI,
job output) · Results & charts · Conclusion · Future work (Spark Streaming, EMR cluster, Athena/QuickSight).

## 8. Possible Extensions
- Scale to `ml-25m` and compare runtime on 1 vs 2+ EC2 nodes (standalone cluster)
- Query results with Athena / visualise with QuickSight or Tableau
- Add tag-genome content features or sentiment on reviews
