"""Build report charts from the CSV outputs (run locally after downloading results from S3)."""
import glob, sys, os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

base = sys.argv[1] if len(sys.argv) > 1 else "output"
os.makedirs("charts", exist_ok=True)

def load(name):
    return pd.read_csv(glob.glob(f"{base}/{name}/csv/part-*.csv")[0])

load("02_rating_distribution").plot.bar(x="rating", y="count", legend=False, title="Rating Distribution")
plt.tight_layout(); plt.savefig("charts/rating_distribution.png"); plt.close()

g = load("07_genre_stats").sort_values("avg_rating")
g.plot.barh(x="genre", y="avg_rating", legend=False, title="Average Rating by Genre")
plt.tight_layout(); plt.savefig("charts/genre_avg_rating.png"); plt.close()

y = load("08_yearly_trend")
y.plot(x="year", y="avg_rating", marker="o", legend=False, title="Average Rating per Year")
plt.tight_layout(); plt.savefig("charts/yearly_trend.png"); plt.close()

t = load("03_top_movies").head(10).sort_values("avg_rating")
t.plot.barh(x="title", y="avg_rating", legend=False, title="Top 10 Movies")
plt.tight_layout(); plt.savefig("charts/top_movies.png"); plt.close()
print("Charts saved in ./charts")
