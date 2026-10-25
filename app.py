
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(
    page_title="Movie Rating Analysis",
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 Movie Rating Analysis Using Spark")
st.write(
    "An interactive dashboard for exploring movie ratings, "
    "movie popularity, and genre statistics."
)

st.sidebar.header("Upload Analysis Data")

uploaded_file = st.sidebar.file_uploader(
    "Upload a ratings CSV file",
    type=["csv"]
)

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)

    st.subheader("Dataset Preview")
    st.dataframe(df.head(100), use_container_width=True)

    st.subheader("Dataset Statistics")
    st.write(f"Total records: {len(df):,}")
    st.write(f"Total columns: {len(df.columns)}")

    if "rating" in df.columns:
        c1, c2, c3 = st.columns(3)

        c1.metric("Total Ratings", f"{len(df):,}")
        c2.metric(
            "Average Rating",
            f"{df['rating'].mean():.2f}"
        )
        c3.metric(
            "Unique Ratings",
            df["rating"].nunique()
        )

        st.subheader("Rating Distribution")
        counts = df["rating"].value_counts().sort_index()

        fig, ax = plt.subplots()
        counts.plot(kind="bar", ax=ax)
        ax.set_xlabel("Rating")
        ax.set_ylabel("Number of Ratings")
        st.pyplot(fig)

    if "title" in df.columns:
        st.subheader("Movie Records")
        st.dataframe(df, use_container_width=True)

else:
    st.info(
        "Upload a CSV file containing movie ratings "
        "to explore the dataset."
    )

st.caption("Movie Rating Analysis | PySpark Big Data PBL")
