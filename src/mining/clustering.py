"""
mining/clustering.py -- K-Means clustering on APSRTC routes.

Features used for clustering (all computed from real APSRTC data):
  - avg_passengers       : average demand per trip
  - max_passengers       : peak demand
  - min_passengers       : off-peak demand
  - trip_count           : route frequency
  - avg_occupancy_rate   : utilisation
  - avg_distance_km      : route length
  - std_passengers       : demand variance
  - avg_revenue          : average revenue

Outputs:
  - outputs/figures/kmeans_elbow.png
  - outputs/figures/kmeans_silhouette.png
  - outputs/figures/kmeans_clusters.png
  - outputs/predictions/route_clusters.csv
"""

import warnings
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import DATA_PROCESSED_DIR, FIGURES_DIR, PREDICTIONS_DIR, RANDOM_SEED
from src.utils.logger import get_logger

warnings.filterwarnings("ignore")
logger = get_logger(__name__)

plt.style.use("seaborn-v0_8-whitegrid")
PALETTE = "tab10"


def build_route_features(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate APSRTC records to route-level features."""
    grp = df.groupby("route")

    features = grp.agg(
        avg_passengers   = ("passengers", "mean"),
        max_passengers   = ("passengers", "max"),
        min_passengers   = ("passengers", "min"),
        std_passengers   = ("passengers", "std"),
        trip_count       = ("passengers", "count"),
        avg_occupancy    = ("occupancy_rate", "mean"),
        avg_distance_km  = ("distance_km", "mean"),
        avg_revenue      = ("revenue", "mean"),
        avg_fare         = ("fare_per_passenger", "mean"),
    ).reset_index()

    features["std_passengers"] = features["std_passengers"].fillna(0)
    logger.info("Route feature matrix: %d routes x %d features", len(features), features.shape[1]-1)
    return features


def elbow_silhouette(X_scaled: np.ndarray, k_range: range) -> tuple[list, list]:
    inertias, sil_scores = [], []
    for k in k_range:
        km = KMeans(n_clusters=k, n_init=10, random_state=RANDOM_SEED)
        labels = km.fit_predict(X_scaled)
        inertias.append(km.inertia_)
        if k > 1:
            sil_scores.append(silhouette_score(X_scaled, labels))
        else:
            sil_scores.append(0)
    return inertias, sil_scores


def plot_elbow(k_range, inertias, sil_scores):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    axes[0].plot(list(k_range), inertias, "bo-", linewidth=2, markersize=7)
    axes[0].set_title("Elbow Method -- Inertia vs K", fontsize=14, fontweight="bold")
    axes[0].set_xlabel("Number of Clusters (K)")
    axes[0].set_ylabel("Inertia")

    axes[1].plot(list(k_range), sil_scores, "rs-", linewidth=2, markersize=7)
    axes[1].set_title("Silhouette Score vs K", fontsize=14, fontweight="bold")
    axes[1].set_xlabel("Number of Clusters (K)")
    axes[1].set_ylabel("Silhouette Score")

    plt.tight_layout()
    out = FIGURES_DIR / "kmeans_elbow_silhouette.png"
    plt.savefig(out, dpi=150)
    plt.close()
    logger.info("Saved elbow+silhouette plot -> %s", out)


def interpret_clusters(features_df: pd.DataFrame, cluster_col: str = "cluster") -> pd.DataFrame:
    """Assign human-readable cluster names based on avg_passengers."""
    stats = features_df.groupby(cluster_col)["avg_passengers"].mean().sort_values()
    n = len(stats)
    labels = {}
    for i, (cid, val) in enumerate(stats.items()):
        if n == 1:
            labels[cid] = "Single Cluster"
        elif i == 0:
            labels[cid] = "Low Demand"
        elif i == n - 1:
            labels[cid] = "High Demand"
        elif i == 1 and n >= 3:
            labels[cid] = "Medium Demand"
        else:
            labels[cid] = "Peak-Dependent"
    features_df["cluster_name"] = features_df[cluster_col].map(labels)
    return features_df, labels


def plot_clusters(features_df: pd.DataFrame):
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    # Scatter: avg_passengers vs avg_occupancy
    for name, grp in features_df.groupby("cluster_name"):
        axes[0].scatter(grp["avg_passengers"], grp["avg_occupancy"],
                        label=name, s=120, alpha=0.8)
    axes[0].set_xlabel("Average Passengers")
    axes[0].set_ylabel("Average Occupancy (%)")
    axes[0].set_title("Route Clusters: Demand vs Occupancy", fontsize=14, fontweight="bold")
    axes[0].legend()

    # Bar: avg_passengers by cluster
    cluster_stats = features_df.groupby("cluster_name")["avg_passengers"].mean().sort_values()
    axes[1].barh(cluster_stats.index, cluster_stats.values,
                 color=sns.color_palette("tab10", len(cluster_stats)))
    axes[1].set_xlabel("Average Passengers")
    axes[1].set_title("Average Demand per Cluster", fontsize=14, fontweight="bold")

    plt.tight_layout()
    out = FIGURES_DIR / "kmeans_clusters.png"
    plt.savefig(out, dpi=150)
    plt.close()
    logger.info("Saved cluster plot -> %s", out)


def run(n_clusters: int = None) -> pd.DataFrame:
    logger.info("=== K-Means Clustering START ===")

    # Load data
    path = DATA_PROCESSED_DIR / "apsrtc_clean.csv"
    if not path.exists():
        logger.error("Run APSRTC ETL first. File not found: %s", path)
        return pd.DataFrame()

    df = pd.read_csv(path)
    logger.info("Loaded APSRTC data: %d rows", len(df))

    # Build route feature matrix
    features = build_route_features(df)
    feature_cols = ["avg_passengers","max_passengers","min_passengers","std_passengers",
                    "trip_count","avg_occupancy","avg_distance_km","avg_revenue"]
    X = features[feature_cols].fillna(0).values

    # Scale
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Determine best K using elbow + silhouette
    k_range = range(2, min(len(features), 9))
    inertias, sil_scores = elbow_silhouette(X_scaled, k_range)
    plot_elbow(k_range, inertias, sil_scores)

    if n_clusters is None:
        # Auto-select: K with best silhouette
        best_idx = int(np.argmax(sil_scores[1:]))  # skip k=1 dummy
        n_clusters = list(k_range)[best_idx + 1]
        logger.info("Auto-selected K=%d (silhouette=%.4f)", n_clusters, sil_scores[best_idx+1])

    # Final K-Means
    km_final = KMeans(n_clusters=n_clusters, n_init=20, random_state=RANDOM_SEED)
    features["cluster"] = km_final.fit_predict(X_scaled)

    # Interpret
    features, cluster_names = interpret_clusters(features, "cluster")

    # Report
    logger.info("\nCluster Summary:")
    summary = features.groupby(["cluster","cluster_name"]).agg(
        routes=("route","count"),
        avg_passengers=("avg_passengers","mean"),
        avg_revenue=("avg_revenue","mean"),
        avg_occupancy=("avg_occupancy","mean"),
    ).reset_index()
    for _, row in summary.iterrows():
        logger.info("  Cluster %d (%s): %d routes | avg_pax=%.1f | avg_rev=%.0f",
                    row["cluster"], row["cluster_name"], row["routes"],
                    row["avg_passengers"], row["avg_revenue"])

    # Plot
    plot_clusters(features)

    # Save
    PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PREDICTIONS_DIR / "route_clusters.csv"
    features.to_csv(out_path, index=False)
    logger.info("Cluster results saved -> %s", out_path)
    logger.info("=== K-Means Clustering END ===")
    return features


if __name__ == "__main__":
    run()
