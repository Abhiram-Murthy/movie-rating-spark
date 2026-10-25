import os
from pathlib import Path
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

st.set_page_config(page_title="Movie Rating Analysis Using Spark", page_icon="🎬", layout="wide")

st.title("🎬 Movie Rating Analysis Using Spark")
st.markdown("Explore movie ratings, popular titles, genre performance, yearly trends, user activity, and available recommendation outputs.")
st.caption("Dashboard note: this app analyzes uploaded CSV data in the dashboard. It does not start a Spark job or connect to AWS automatically.")

RESULT_DIR = Path("output")


def read_csv_upload(uploaded, label):
    if uploaded is None:
        return None
    try:
        return pd.read_csv(uploaded)
    except Exception as exc:
        st.error(f"Could not read {label}: {exc}")
        return None


def find_result_csv(folder_name):
    folder = RESULT_DIR / folder_name
    if not folder.exists():
        return None
    candidates = list(folder.glob("*.csv"))
    if not candidates:
        candidates = list(folder.glob("csv/*.csv"))
    if not candidates:
        candidates = list(folder.rglob("part-*.csv"))
    if not candidates:
        return None
    try:
        return pd.read_csv(candidates[0])
    except Exception:
        return None

with st.sidebar:
    st.header("Data sources")
    st.write("Upload MovieLens input files, or place generated CSV outputs under `output/` in the GitHub repository.")
    ratings_file = st.file_uploader("Upload ratings.csv", type=["csv"], key="ratings")
    movies_file = st.file_uploader("Upload movies.csv", type=["csv"], key="movies")
    st.divider()
    st.subheader("Optional Spark outputs")
    top_file = st.file_uploader("03_top_movies CSV (optional)", type=["csv"], key="top")
    weighted_file = st.file_uploader("06_weighted_top_movies CSV (optional)", type=["csv"], key="weighted")
    genre_file = st.file_uploader("07_genre_stats CSV (optional)", type=["csv"], key="genre")
    yearly_file = st.file_uploader("08_yearly_trend CSV (optional)", type=["csv"], key="yearly")
    users_file = st.file_uploader("10_user_segments CSV (optional)", type=["csv"], key="segments")
    recs_file = st.file_uploader("11_als_recommendations CSV (optional)", type=["csv"], key="recs")

ratings = read_csv_upload(ratings_file, "ratings.csv")
movies = read_csv_upload(movies_file, "movies.csv")

# Fall back to checked-in input files if available.
if ratings is None and Path("data/ratings.csv").exists():
    ratings = pd.read_csv("data/ratings.csv")
if movies is None and Path("data/movies.csv").exists():
    movies = pd.read_csv("data/movies.csv")

# Prefer uploaded Spark outputs; otherwise load locally committed output CSVs.
top_df = read_csv_upload(top_file, "top movies") if top_file else find_result_csv("03_top_movies")
weighted_df = read_csv_upload(weighted_file, "weighted top movies") if weighted_file else find_result_csv("06_weighted_top_movies")
genre_df = read_csv_upload(genre_file, "genre statistics") if genre_file else find_result_csv("07_genre_stats")
yearly_df = read_csv_upload(yearly_file, "yearly trend") if yearly_file else find_result_csv("08_yearly_trend")
segments_df = read_csv_upload(users_file, "user segments") if users_file else find_result_csv("10_user_segments")
recs_df = read_csv_upload(recs_file, "ALS recommendations") if recs_file else find_result_csv("11_als_recommendations")

if ratings is not None:
    required = {"userId", "movieId", "rating"}
    if not required.issubset(ratings.columns):
        st.error("ratings.csv must contain userId, movieId, and rating columns. MovieLens ratings.csv also contains timestamp.")
        ratings = None
    else:
        ratings = ratings.copy()
        for col in ["userId", "movieId", "rating", "timestamp"]:
            if col in ratings.columns:
                ratings[col] = pd.to_numeric(ratings[col], errors="coerce")
        ratings = ratings.dropna(subset=["userId", "movieId", "rating"])
        ratings = ratings[ratings["rating"].between(0.5, 5.0)]
        ratings = ratings.drop_duplicates(["userId", "movieId"])

if ratings is not None and movies is not None:
    if not {"movieId", "title"}.issubset(movies.columns):
        st.error("movies.csv must contain movieId and title columns; genres is recommended.")
        movies = None
    else:
        movies = movies.copy()
        movies["movieId"] = pd.to_numeric(movies["movieId"], errors="coerce")
        movies = movies.dropna(subset=["movieId"]).drop_duplicates("movieId")

if ratings is not None:
    st.subheader("Dataset overview")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Valid ratings", f"{len(ratings):,}")
    c2.metric("Unique users", f"{ratings['userId'].nunique():,}")
    c3.metric("Movies rated", f"{ratings['movieId'].nunique():,}")
    c4.metric("Mean rating", f"{ratings['rating'].mean():.3f} / 5")

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Rating distribution")
        dist = ratings.groupby("rating").size().sort_index()
        fig, ax = plt.subplots()
        dist.plot(kind="bar", ax=ax)
        ax.set_xlabel("Rating")
        ax.set_ylabel("Number of ratings")
        ax.tick_params(axis="x", rotation=0)
        st.pyplot(fig, clear_figure=True)
    with c2:
        st.subheader("Rating summary")
        summary = pd.DataFrame({"Metric": ["Total ratings", "Unique users", "Movies rated", "Mean rating", "Standard deviation"],
                                "Value": [f"{len(ratings):,}", f"{ratings.userId.nunique():,}", f"{ratings.movieId.nunique():,}", f"{ratings.rating.mean():.3f}", f"{ratings.rating.std():.3f}"]})
        st.dataframe(summary, hide_index=True, use_container_width=True)

    if movies is not None:
        movie_stats = ratings.groupby("movieId").agg(num_ratings=("rating", "size"), avg_rating=("rating", "mean")).reset_index()
        movie_stats = movie_stats.merge(movies, on="movieId", how="left")
        movie_stats["title"] = movie_stats["title"].fillna(movie_stats["movieId"].astype(str))
        global_mean = ratings["rating"].mean()
        min_votes = st.sidebar.slider("Minimum ratings for ranking", min_value=1, max_value=100, value=20)
        movie_stats["weighted_rating"] = ((movie_stats["num_ratings"] / (movie_stats["num_ratings"] + min_votes)) * movie_stats["avg_rating"] + (min_votes / (movie_stats["num_ratings"] + min_votes)) * global_mean)
        eligible = movie_stats[movie_stats["num_ratings"] >= min_votes]

        st.subheader("Movie rankings")
        tab1, tab2, tab3 = st.tabs(["Top rated", "Most rated", "Weighted rating"])
        with tab1:
            shown = top_df if top_df is not None else eligible.sort_values(["avg_rating", "num_ratings"], ascending=[False, False]).head(20)
            st.dataframe(shown, hide_index=True, use_container_width=True)
        with tab2:
            st.dataframe(movie_stats.sort_values("num_ratings", ascending=False).head(20), hide_index=True, use_container_width=True)
        with tab3:
            shown = weighted_df if weighted_df is not None else movie_stats.sort_values("weighted_rating", ascending=False).head(20)
            st.dataframe(shown, hide_index=True, use_container_width=True)

        if "genres" in movies.columns:
            if genre_df is None:
                genre_rows = ratings[["movieId", "rating"]].merge(movies[["movieId", "genres"]], on="movieId", how="left")
                genre_rows["genre"] = genre_rows["genres"].fillna("(no genres listed)").str.split("|")
                genre_rows = genre_rows.explode("genre")
                genre_df = genre_rows.groupby("genre").agg(num_ratings=("rating", "size"), avg_rating=("rating", "mean")).reset_index().sort_values("avg_rating", ascending=False)
            if {"genre", "avg_rating"}.issubset(genre_df.columns):
                st.subheader("Average rating by genre")
                plot_df = genre_df.sort_values("avg_rating", ascending=True).tail(20)
                fig, ax = plt.subplots(figsize=(9, max(4, len(plot_df) * 0.28)))
                ax.barh(plot_df["genre"].astype(str), plot_df["avg_rating"])
                ax.set_xlabel("Average rating")
                ax.set_ylabel("Genre")
                st.pyplot(fig, clear_figure=True)
                st.dataframe(genre_df, hide_index=True, use_container_width=True)

    if "timestamp" in ratings.columns:
        years = pd.to_datetime(ratings["timestamp"], unit="s", errors="coerce").dt.year
        year_df = pd.DataFrame({"year": years, "rating": ratings["rating"]}).dropna().groupby("year").agg(num_ratings=("rating", "size"), avg_rating=("rating", "mean")).reset_index()
        if not year_df.empty:
            st.subheader("Yearly rating trend")
            if yearly_df is not None and {"year", "avg_rating"}.issubset(yearly_df.columns):
                chart_df = yearly_df.sort_values("year")
            else:
                chart_df = year_df.sort_values("year")
            st.line_chart(chart_df.set_index("year")["avg_rating"])
            st.dataframe(chart_df, hide_index=True, use_container_width=True)

    user_stats = ratings.groupby("userId").agg(num_ratings=("rating", "size"), avg_rating=("rating", "mean")).reset_index()
    user_stats["segment"] = user_stats["num_ratings"].apply(lambda n: "Heavy" if n >= 200 else ("Regular" if n >= 50 else "Light"))
    st.subheader("User activity segments")
    if segments_df is not None:
        st.dataframe(segments_df, hide_index=True, use_container_width=True)
    else:
        seg = user_stats.groupby("segment").agg(users=("userId", "nunique"), avg_rating=("avg_rating", "mean")).reset_index()
        st.dataframe(seg, hide_index=True, use_container_width=True)
        st.bar_chart(seg.set_index("segment")["users"])

else:
    st.info("Upload both MovieLens files in the sidebar: ratings.csv and movies.csv. The dashboard will calculate the analysis from those files.")
    st.markdown("**Expected columns**  \n- `ratings.csv`: `userId`, `movieId`, `rating`, `timestamp`  \n- `movies.csv`: `movieId`, `title`, `genres`")

if recs_df is not None:
    st.subheader("ALS recommendations")
    st.caption("These recommendations are displayed from a supplied Spark output CSV; this dashboard does not train ALS itself.")
    st.dataframe(recs_df, hide_index=True, use_container_width=True)
else:
    st.subheader("ALS recommendations")
    st.info("No ALS recommendation output was found. Upload `11_als_recommendations.csv` in the sidebar after running the Spark job with `--als`.")

st.divider()
st.caption("Movie Rating Analysis PBL | Streamlit dashboard")
