"""
mining/clustering.py -- K-Means clustering on all 3 transport modes.

Loads: apsrtc_clean.csv, railways_clean.csv, flights_clean.csv
Clusters routes across Bus + Rail + Air using shared demand features.
A transport_mode column distinguishes each mode in the output.

Features used for clustering (computed per route across all modes):
  - avg_passengers     : average demand per trip
  - max_passengers     : peak demand
  - min_passengers     : off-peak demand
  - std_passengers     : demand variance
  - trip_count         : route frequency
  - avg_occupancy      : utilisation (capacity fill rate)
  - avg_distance_km    : route length
  - avg_fare           : average fare/price

Outputs:
  - outputs/figures/kmeans_elbow_silhouette.png
  - outputs/figures/kmeans_clusters.png
  - outputs/predictions/route_clusters.csv  (all 3 modes)
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


# ── Data loading ──────────────────────────────────────────────────────────────

def _load_apsrtc(processed_dir: Path) -> pd.DataFrame:
    path = processed_dir / "apsrtc_clean.csv"
    if not path.exists():
        logger.warning("APSRTC clean data not found: %s", path)
        return pd.DataFrame()
    df = pd.read_csv(path)
    df["transport_mode"] = "Bus"
    df["route"]          = df["route"].astype(str).str.title()
    df["distance_km"]    = pd.to_numeric(df.get("distance_km"), errors="coerce")
    df["fare"]           = pd.to_numeric(df.get("fare_per_passenger"), errors="coerce")
    df["occupancy"]      = pd.to_numeric(df.get("occupancy_rate"), errors="coerce")
    df["passengers"]     = pd.to_numeric(df.get("passengers"), errors="coerce")
    logger.info("APSRTC loaded: %d rows", len(df))
    return df[["transport_mode", "route", "passengers", "distance_km", "fare", "occupancy"]]


def _load_railways(processed_dir: Path) -> pd.DataFrame:
    path = processed_dir / "railways_clean.csv"
    if not path.exists():
        logger.warning("Railways clean data not found: %s", path)
        return pd.DataFrame()
    df = pd.read_csv(path, low_memory=False)
    if "passengers" not in df.columns:
        logger.warning("No passengers column in railways data — skipping.")
        return pd.DataFrame()
    df["transport_mode"] = "Rail"
    df["route"]          = (df.get("source_station", "").astype(str).str.title() + "-" +
                            df.get("destination_station", "").astype(str).str.title())
    df["distance_km"]    = pd.to_numeric(df.get("distance"), errors="coerce")
    df["fare"]           = (df["distance_km"] * 0.5).clip(lower=30)  # approx INR/km
    df["capacity"]       = df["distance_km"].apply(
        lambda d: 800 if d > 1000 else (500 if d > 400 else 200)
    )
    df["occupancy"]      = (pd.to_numeric(df["passengers"], errors="coerce") /
                            df["capacity"] * 100).clip(upper=100)
    df["passengers"]     = pd.to_numeric(df.get("passengers"), errors="coerce")
    logger.info("Railways loaded: %d rows", len(df))
    return df[["transport_mode", "route", "passengers", "distance_km", "fare", "occupancy"]]


def _load_flights(processed_dir: Path) -> pd.DataFrame:
    path = processed_dir / "flights_clean.csv"
    if not path.exists():
        logger.warning("Flights clean data not found: %s", path)
        return pd.DataFrame()
    df = pd.read_csv(path, low_memory=False)
    if "passengers" not in df.columns:
        logger.warning("No passengers column in flights data — skipping.")
        return pd.DataFrame()
    df["transport_mode"] = "Air"
    src = df.get("source", pd.Series(dtype=str)).astype(str).str.title()
    dst = df.get("destination", pd.Series(dtype=str)).astype(str).str.title()
    df["route"]       = src + "-" + dst
    df["distance_km"] = pd.to_numeric(df.get("duration_minutes", 60), errors="coerce").fillna(60) * 8.5
    df["fare"]        = pd.to_numeric(df.get("price"), errors="coerce")
    capacity          = pd.to_numeric(df.get("airline_tier", 2), errors="coerce").map(
        {1: 250, 2: 160, 3: 72}
    ).fillna(160)
    df["occupancy"]   = (pd.to_numeric(df["passengers"], errors="coerce") / capacity * 100).clip(upper=100)
    df["passengers"]  = pd.to_numeric(df.get("passengers"), errors="coerce")
    logger.info("Flights loaded: %d rows", len(df))
    return df[["transport_mode", "route", "passengers", "distance_km", "fare", "occupancy"]]


def load_all(processed_dir: Path) -> pd.DataFrame:
    """Merge all 3 transport datasets into a unified DataFrame."""
    frames = [
        _load_apsrtc(processed_dir),
        _load_railways(processed_dir),
        _load_flights(processed_dir),
    ]
    frames = [f for f in frames if not f.empty]
    if not frames:
        raise FileNotFoundError("No processed datasets found. Run ETL first.")
    df = pd.concat(frames, ignore_index=True)
    df = df.dropna(subset=["passengers"])
    logger.info(
        "Combined dataset: %d rows | Bus=%d  Rail=%d  Air=%d",
        len(df),
        (df["transport_mode"] == "Bus").sum(),
        (df["transport_mode"] == "Rail").sum(),
        (df["transport_mode"] == "Air").sum(),
    )
    return df


# ── Feature engineering ───────────────────────────────────────────────────────

def build_route_features(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate to route-level features, keeping transport_mode."""
    grp = df.groupby(["route", "transport_mode"])

    features = grp.agg(
        avg_passengers  = ("passengers", "mean"),
        max_passengers  = ("passengers", "max"),
        min_passengers  = ("passengers", "min"),
        std_passengers  = ("passengers", "std"),
        trip_count      = ("passengers", "count"),
        avg_occupancy   = ("occupancy",  "mean"),
        avg_distance_km = ("distance_km","mean"),
        avg_fare        = ("fare",        "mean"),
    ).reset_index()

    features["std_passengers"] = features["std_passengers"].fillna(0)
    features["avg_occupancy"]  = features["avg_occupancy"].fillna(0)
    features["avg_fare"]       = features["avg_fare"].fillna(0)
    logger.info(
        "Route feature matrix: %d routes x %d features | Bus=%d  Rail=%d  Air=%d",
        len(features), features.shape[1] - 2,
        (features["transport_mode"] == "Bus").sum(),
        (features["transport_mode"] == "Rail").sum(),
        (features["transport_mode"] == "Air").sum(),
    )
    return features


# ── Clustering utilities ──────────────────────────────────────────────────────

def elbow_silhouette(X_scaled: np.ndarray, k_range: range) -> tuple[list, list]:
    inertias, sil_scores = [], []
    sample_sz = min(3000, len(X_scaled)) if len(X_scaled) > 0 else None
    for k in k_range:
        km = KMeans(n_clusters=k, n_init=10, random_state=RANDOM_SEED)
        labels = km.fit_predict(X_scaled)
        inertias.append(km.inertia_)
        sil_scores.append(
            silhouette_score(X_scaled, labels, sample_size=sample_sz, random_state=RANDOM_SEED)
            if k > 1 else 0
        )
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
    for i, (cid, _) in enumerate(stats.items()):
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
    """Scatter and bar charts coloured by transport mode and cluster."""
    fig, axes = plt.subplots(1, 2, figsize=(18, 7))
    mode_colors = {"Bus": "steelblue", "Rail": "darkorange", "Air": "seagreen"}

    # Scatter: avg_passengers vs avg_occupancy, shape=cluster, colour=mode
    for mode, grp in features_df.groupby("transport_mode"):
        axes[0].scatter(
            grp["avg_passengers"], grp["avg_occupancy"],
            label=mode, color=mode_colors.get(mode, "grey"),
            s=60, alpha=0.7
        )
    axes[0].set_xlabel("Average Passengers")
    axes[0].set_ylabel("Average Occupancy (%)")
    axes[0].set_title("Route Clusters: Demand vs Occupancy\n(All Transport Modes)",
                      fontsize=13, fontweight="bold")
    axes[0].legend(title="Transport Mode")

    # Bar: avg_passengers per cluster, stacked by mode
    cluster_mode = features_df.groupby(["cluster_name", "transport_mode"])["avg_passengers"].mean().unstack(fill_value=0)
    cluster_mode.plot(kind="barh", ax=axes[1], color=[mode_colors.get(m, "grey") for m in cluster_mode.columns])
    axes[1].set_xlabel("Average Passengers")
    axes[1].set_title("Average Demand per Cluster by Mode", fontsize=13, fontweight="bold")
    axes[1].legend(title="Transport Mode")

    plt.tight_layout()
    out = FIGURES_DIR / "kmeans_clusters.png"
    plt.savefig(out, dpi=150)
    plt.close()
    logger.info("Saved cluster plot -> %s", out)


# ── Main entry point ──────────────────────────────────────────────────────────

def run(n_clusters: int = None) -> pd.DataFrame:
    logger.info("=== K-Means Clustering START (Bus + Rail + Air) ===")

    df = load_all(DATA_PROCESSED_DIR)
    features = build_route_features(df)

    FEATURE_COLS = [
        "avg_passengers", "max_passengers", "min_passengers", "std_passengers",
        "trip_count", "avg_occupancy", "avg_distance_km", "avg_fare",
    ]
    X = features[FEATURE_COLS].fillna(0).values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Elbow + Silhouette to auto-select K
    k_range = range(2, min(len(features), 9))
    inertias, sil_scores = elbow_silhouette(X_scaled, k_range)
    plot_elbow(k_range, inertias, sil_scores)

    if n_clusters is None:
        best_idx   = int(np.argmax(sil_scores))
        n_clusters = list(k_range)[best_idx]
        logger.info("Auto-selected K=%d (silhouette=%.4f)", n_clusters, sil_scores[best_idx])

    # Final K-Means
    km_final = KMeans(n_clusters=n_clusters, n_init=20, random_state=RANDOM_SEED)
    features["cluster"] = km_final.fit_predict(X_scaled)

    features, cluster_names = interpret_clusters(features, "cluster")

    # Summary log
    logger.info("\nCluster Summary (all modes):")
    summary = features.groupby(["cluster", "cluster_name", "transport_mode"]).agg(
        routes        = ("route",          "count"),
        avg_passengers= ("avg_passengers", "mean"),
        avg_fare      = ("avg_fare",       "mean"),
        avg_occupancy = ("avg_occupancy",  "mean"),
    ).reset_index()
    for _, row in summary.iterrows():
        logger.info(
            "  Cluster %d (%s) [%s]: %d routes | avg_pax=%.1f | avg_fare=%.0f | avg_occ=%.1f%%",
            row["cluster"], row["cluster_name"], row["transport_mode"],
            row["routes"], row["avg_passengers"], row["avg_fare"], row["avg_occupancy"]
        )

    plot_clusters(features)

    PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PREDICTIONS_DIR / "route_clusters.csv"
    features.to_csv(out_path, index=False)
    logger.info("Cluster results saved -> %s", out_path)
    logger.info("=== K-Means Clustering END ===")
    return features


if __name__ == "__main__":
    run()
