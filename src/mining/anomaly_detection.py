"""
mining/anomaly_detection.py -- Isolation Forest anomaly detection on APSRTC data.

Reports:
  - Number and percentage of anomalies
  - Routes with most anomalies
  - Temporal pattern of anomalies
  - Extreme demand records

Outputs:
  - outputs/predictions/apsrtc_anomalies.csv
  - outputs/figures/anomaly_scatter.png
  - outputs/figures/anomaly_by_route.png
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
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import DATA_PROCESSED_DIR, FIGURES_DIR, PREDICTIONS_DIR, RANDOM_SEED
from src.utils.logger import get_logger

warnings.filterwarnings("ignore")
logger = get_logger(__name__)
plt.style.use("seaborn-v0_8-whitegrid")


FEATURE_COLS = [
    "passengers", "occupancy_rate", "distance_km",
    "revenue", "fare_per_passenger", "fuel_consumed_liters"
]


def run(contamination: float = 0.05) -> pd.DataFrame:
    logger.info("=== Isolation Forest Anomaly Detection START ===")

    path = DATA_PROCESSED_DIR / "apsrtc_clean.csv"
    if not path.exists():
        logger.error("Run APSRTC ETL first. File not found: %s", path)
        return pd.DataFrame()

    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    logger.info("Loaded APSRTC clean data: %d rows", len(df))

    # Features for anomaly detection
    avail_cols = [c for c in FEATURE_COLS if c in df.columns]
    X = df[avail_cols].fillna(0).values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Isolation Forest
    iso = IsolationForest(
        contamination=contamination,
        n_estimators=200,
        random_state=RANDOM_SEED,
        n_jobs=-1,
    )
    df["anomaly_score"] = -iso.fit_predict(X_scaled)   # -1=anomaly -> 1, 1=normal -> -1 … invert
    df["anomaly_score"] = iso.score_samples(X_scaled)   # real scores (more negative = more anomalous)
    df["is_anomaly"]    = (iso.fit_predict(X_scaled) == -1).astype(int)

    n_total    = len(df)
    n_anomaly  = df["is_anomaly"].sum()
    pct        = 100 * n_anomaly / n_total

    logger.info("Total records  : %d", n_total)
    logger.info("Anomalies found: %d (%.2f%%)", n_anomaly, pct)

    anomalies = df[df["is_anomaly"] == 1].copy()

    # -- Report by route -------------------------------------------------------
    if "route" in anomalies.columns:
        route_anom = anomalies.groupby("route").size().sort_values(ascending=False)
        logger.info("\nTop routes with anomalies:\n%s", route_anom.head(10).to_string())

    # -- Extreme demand anomalies ----------------------------------------------
    if "passengers" in anomalies.columns:
        extreme = anomalies.nlargest(5, "passengers")[["date","route","passengers","anomaly_score"]]
        logger.info("\nHighest anomalous passenger records:\n%s", extreme.to_string())

    # -- Plots -----------------------------------------------------------------
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    # Scatter: passengers vs occupancy, coloured by anomaly
    normal = df[df["is_anomaly"] == 0]
    anom   = df[df["is_anomaly"] == 1]
    axes[0].scatter(normal["passengers"], normal["occupancy_rate"],
                    c="steelblue", alpha=0.4, s=20, label="Normal")
    axes[0].scatter(anom["passengers"], anom["occupancy_rate"],
                    c="crimson", alpha=0.8, s=40, label=f"Anomaly ({n_anomaly})")
    axes[0].set_xlabel("Passengers")
    axes[0].set_ylabel("Occupancy Rate (%)")
    axes[0].set_title("Isolation Forest -- Anomalies in Demand Space",
                      fontsize=13, fontweight="bold")
    axes[0].legend()

    # Bar: anomalies per route
    if "route" in df.columns:
        route_counts = df[df["is_anomaly"]==1].groupby("route").size().sort_values(ascending=False).head(10)
        axes[1].barh(route_counts.index, route_counts.values, color="crimson", alpha=0.8)
        axes[1].set_xlabel("Anomaly Count")
        axes[1].set_title("Top Routes by Anomaly Count", fontsize=13, fontweight="bold")

    plt.tight_layout()
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    plt.savefig(FIGURES_DIR / "anomaly_detection.png", dpi=150)
    plt.close()
    logger.info("Saved anomaly plot -> %s", FIGURES_DIR / "anomaly_detection.png")

    # -- Save results ---------------------------------------------------------
    PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PREDICTIONS_DIR / "apsrtc_anomalies.csv"
    df[["date","route","bus_type","passengers","occupancy_rate",
        "revenue","anomaly_score","is_anomaly"]].to_csv(out_path, index=False)
    logger.info("Anomaly results saved -> %s", out_path)

    logger.info("=== Isolation Forest Anomaly Detection END ===")
    return df


if __name__ == "__main__":
    run()
