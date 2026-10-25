"""
Movie Rating Analysis using Apache Spark (PySpark)
Reads MovieLens-style ratings.csv / movies.csv from a local path or S3 (s3a://),
runs the analyses, and writes results back as Parquet/CSV.

Usage:
  Local : spark-submit src/movie_rating_analysis.py --input data --output output
  AWS   : spark-submit src/movie_rating_analysis.py \
            --input s3a://<bucket>/raw --output s3a://<bucket>/results
"""
import argparse
from pyspark.sql import SparkSession, functions as F
from pyspark.sql.types import (StructType, StructField, IntegerType,
                               DoubleType, LongType, StringType)

RATINGS_SCHEMA = StructType([
    StructField("userId", IntegerType()), StructField("movieId", IntegerType()),
    StructField("rating", DoubleType()), StructField("timestamp", LongType())])
MOVIES_SCHEMA = StructType([
    StructField("movieId", IntegerType()), StructField("title", StringType()),
    StructField("genres", StringType())])


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, help="Folder containing ratings.csv and movies.csv")
    p.add_argument("--output", required=True, help="Output folder (local or s3a://)")
    p.add_argument("--min-ratings", type=int, default=50, help="Min ratings for 'top movies'")
    p.add_argument("--als", action="store_true", help="Also train an ALS recommender")
    return p.parse_args()


def save(df, path, name):
    """Write as Parquet (analytics) and a single CSV (easy to open / chart)."""
    df.write.mode("overwrite").parquet(f"{path}/{name}/parquet")
    df.coalesce(1).write.mode("overwrite").option("header", True).csv(f"{path}/{name}/csv")


def main():
    args = parse_args()
    spark = (SparkSession.builder.appName("MovieRatingAnalysis")
             .config("spark.sql.shuffle.partitions", "64")
             .getOrCreate())
    spark.sparkContext.setLogLevel("WARN")

    ratings = spark.read.csv(f"{args.input}/ratings.csv", header=True, schema=RATINGS_SCHEMA)
    movies = spark.read.csv(f"{args.input}/movies.csv", header=True, schema=MOVIES_SCHEMA)

    # ---- Cleaning ----
    ratings = (ratings.dropna().dropDuplicates(["userId", "movieId"])
               .filter(F.col("rating").between(0.5, 5.0))
               .withColumn("rated_at", F.from_unixtime("timestamp").cast("timestamp"))
               .withColumn("year", F.year("rated_at")).cache())
    print(f"Ratings: {ratings.count():,} | Movies: {movies.count():,}")

    # ---- 1. Overall summary ----
    summary = ratings.agg(
        F.count("*").alias("total_ratings"),
        F.countDistinct("userId").alias("users"),
        F.countDistinct("movieId").alias("movies_rated"),
        F.round(F.avg("rating"), 3).alias("avg_rating"),
        F.round(F.stddev("rating"), 3).alias("std_rating"))
    summary.show(truncate=False); save(summary, args.output, "01_summary")

    # ---- 2. Rating distribution ----
    dist = ratings.groupBy("rating").count().orderBy("rating")
    dist.show(); save(dist, args.output, "02_rating_distribution")

    # ---- 3. Per-movie stats + Top / Bottom movies ----
    stats = (ratings.groupBy("movieId")
             .agg(F.count("*").alias("num_ratings"), F.round(F.avg("rating"), 3).alias("avg_rating"))
             .join(movies, "movieId"))
    top = (stats.filter(F.col("num_ratings") >= args.min_ratings)
           .orderBy(F.desc("avg_rating"), F.desc("num_ratings")).limit(20))
    bottom = (stats.filter(F.col("num_ratings") >= args.min_ratings)
              .orderBy("avg_rating", F.desc("num_ratings")).limit(20))
    most_rated = stats.orderBy(F.desc("num_ratings")).limit(20)
    top.show(20, truncate=False)
    save(top, args.output, "03_top_movies")
    save(bottom, args.output, "04_bottom_movies")
    save(most_rated, args.output, "05_most_rated_movies")

    # ---- 4. Bayesian weighted rating (IMDb-style) ----
    C = ratings.agg(F.avg("rating")).first()[0]
    m = args.min_ratings
    weighted = (stats.withColumn("weighted_rating", F.round(
        (F.col("num_ratings") / (F.col("num_ratings") + m)) * F.col("avg_rating") +
        (m / (F.col("num_ratings") + m)) * F.lit(C), 3))
        .orderBy(F.desc("weighted_rating")).limit(20))
    save(weighted, args.output, "06_weighted_top_movies")

    # ---- 5. Genre analysis ----
    genre = (ratings.join(movies, "movieId")
             .withColumn("genre", F.explode(F.split("genres", r"\|")))
             .groupBy("genre")
             .agg(F.count("*").alias("num_ratings"), F.round(F.avg("rating"), 3).alias("avg_rating"))
             .orderBy(F.desc("avg_rating")))
    genre.show(truncate=False); save(genre, args.output, "07_genre_stats")

    # ---- 6. Trend over time ----
    yearly = (ratings.groupBy("year")
              .agg(F.count("*").alias("num_ratings"), F.round(F.avg("rating"), 3).alias("avg_rating"))
              .orderBy("year"))
    save(yearly, args.output, "08_yearly_trend")

    # ---- 7. User behaviour ----
    users = (ratings.groupBy("userId")
             .agg(F.count("*").alias("num_ratings"), F.round(F.avg("rating"), 3).alias("avg_rating"))
             .orderBy(F.desc("num_ratings")))
    save(users.limit(100), args.output, "09_top_active_users")
    user_buckets = (users.withColumn("segment", F.when(F.col("num_ratings") >= 200, "Heavy")
                    .when(F.col("num_ratings") >= 50, "Regular").otherwise("Light"))
                    .groupBy("segment").agg(F.count("*").alias("users"),
                                            F.round(F.avg("avg_rating"), 3).alias("avg_rating")))
    save(user_buckets, args.output, "10_user_segments")

    # ---- 8. (Optional) ALS recommender ----
    if args.als:
        from pyspark.ml.recommendation import ALS
        from pyspark.ml.evaluation import RegressionEvaluator
        train, test = ratings.select("userId", "movieId", "rating").randomSplit([0.8, 0.2], seed=42)
        als = ALS(userCol="userId", itemCol="movieId", ratingCol="rating",
                  rank=10, maxIter=10, regParam=0.1, coldStartStrategy="drop")
        model = als.fit(train)
        rmse = RegressionEvaluator(metricName="rmse", labelCol="rating",
                                   predictionCol="prediction").evaluate(model.transform(test))
        print(f"ALS RMSE = {rmse:.4f}")
        recs = (model.recommendForAllUsers(5)
                .select("userId", F.explode("recommendations").alias("rec"))
                .select("userId", F.col("rec.movieId").alias("movieId"), F.round("rec.rating", 3).alias("pred")))
        save(recs.join(movies, "movieId"), args.output, "11_als_recommendations")

    spark.stop()


if __name__ == "__main__":
    main()
