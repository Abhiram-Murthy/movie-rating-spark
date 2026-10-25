"""Generate a small MovieLens-shaped dataset for local testing (no download needed)."""
import csv, random, os, time

random.seed(42)
out = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(out, exist_ok=True)

GENRES = ["Action", "Adventure", "Comedy", "Drama", "Sci-Fi", "Thriller", "Romance", "Animation", "Horror"]
N_MOVIES, N_USERS, N_RATINGS = 300, 500, 20000

with open(os.path.join(out, "movies.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["movieId", "title", "genres"])
    for m in range(1, N_MOVIES + 1):
        year = random.randint(1980, 2020)
        g = "|".join(random.sample(GENRES, random.randint(1, 3)))
        w.writerow([m, f"Movie {m} ({year})", g])

quality = {m: random.uniform(2.0, 4.5) for m in range(1, N_MOVIES + 1)}
now = int(time.time())
with open(os.path.join(out, "ratings.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["userId", "movieId", "rating", "timestamp"])
    seen = set()
    while len(seen) < N_RATINGS:
        u, m = random.randint(1, N_USERS), random.randint(1, N_MOVIES)
        if (u, m) in seen: continue
        seen.add((u, m))
        r = min(5.0, max(0.5, round((quality[m] + random.gauss(0, 0.8)) * 2) / 2))
        w.writerow([u, m, r, now - random.randint(0, 20 * 365 * 86400)])
print("Sample data written to", os.path.abspath(out))
