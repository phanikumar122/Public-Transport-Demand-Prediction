"""
mining/anomaly_detection.py -- Isolation Forest anomaly detection across all 3 transport modes.

Loads: apsrtc_clean.csv, railways_clean.csv, flights_clean.csv
Detects anomalous trips across Bus + Rail + Air using shared demand features.

Shared features used (columns available in all 3 datasets):
  - passengers       : demand count
  - occupancy_rate   : % capacity filled
  - distance_km      : route length
  - fare_per_passenger / price : ticket cost

Mode-specific features used where available:
  - Bus  : fuel_consumed_liters, revenue
  - Rail : num_classes, num_intermediate_stops
  - Air  : num_stops, duration_minutes

Outputs:
  - outputs/predictions/transport_anomalies.csv  (all 3 modes)
  - outputs/figures/anomaly_detection.png
  - outputs/figures/anomaly_by_mode.png
"""

import warnings
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import DATA_PROCESSED_DIR, FIGURES_DIR, PREDICTIONS_DIR, RANDOM_SEED
from src.utils.logger import get_logger

warnings.filterwarnings("ignore")
logger = get_logger(__name__)
plt.style.use("seaborn-v0_8-whitegrid")

# Shared features present (or derivable) in all 3 datasets
SHARED_FEATURES = ["passengers", "occupancy_rate", "distance_km", "fare_per_passenger"]


# ── Data loading ──────────────────────────────────────────────────────────────

def _load_apsrtc(processed_dir: Path) -> pd.DataFrame:
    path = processed_dir / "apsrtc_clean.csv"
    if not path.exists():
        logger.warning("APSRTC clean not found: %s", path)
        return pd.DataFrame()
    df = pd.read_csv(path)
    df["transport_mode"] = "Bus"
    df["distance_km"]        = pd.to_numeric(df.get("distance_km"),          errors="coerce")
    df["fare_per_passenger"]  = pd.to_numeric(df.get("fare_per_passenger"),   errors="coerce")
    df["passengers"]          = pd.to_numeric(df.get("passengers"),           errors="coerce")
    df["occupancy_rate"]      = pd.to_numeric(df.get("occupancy_rate"),       errors="coerce")
    # Bus-specific extras
    df["revenue"]             = pd.to_numeric(df.get("revenue"),              errors="coerce")
    df["fuel_consumed_liters"]= pd.to_numeric(df.get("fuel_consumed_liters"), errors="coerce")
    df["route"]               = df.get("route",    "Unknown").astype(str)
    df["mode_type"]           = df.get("bus_type", "Unknown").astype(str)
    keep = ["transport_mode", "route", "mode_type", "passengers", "occupancy_rate",
            "distance_km", "fare_per_passenger", "revenue", "fuel_consumed_liters"]
    logger.info("APSRTC loaded: %d rows", len(df))
    return df[[c for c in keep if c in df.columns]]


def _load_railways(processed_dir: Path) -> pd.DataFrame:
    path = processed_dir / "railways_clean.csv"
    if not path.exists():
        logger.warning("Railways clean not found: %s", path)
        return pd.DataFrame()
    df = pd.read_csv(path, low_memory=False)
    if "passengers" not in df.columns:
        logger.warning("No passengers column in railways — skipping anomaly detection for Rail.")
        return pd.DataFrame()
    df["transport_mode"]     = "Rail"
    df["distance_km"]        = pd.to_numeric(df.get("distance"),    errors="coerce")
    df["fare_per_passenger"] = (df["distance_km"] * 0.5).clip(lower=30)
    df["passengers"]         = pd.to_numeric(df.get("passengers"),  errors="coerce")
    capacity                 = df["distance_km"].apply(
        lambda d: 800 if d > 1000 else (500 if d > 400 else 200)
    )
    df["occupancy_rate"]     = (df["passengers"] / capacity * 100).clip(upper=100)
    df["route"]              = (df.get("source_station", "").astype(str).str.title() + "-" +
                                df.get("destination_station", "").astype(str).str.title())
    df["mode_type"]          = df.get("train_type", "Express").astype(str)
    # Rail-specific extras
    df["num_classes"]        = pd.to_numeric(df.get("num_classes"),              errors="coerce").fillna(0)
    df["num_intermediate_stops"] = pd.to_numeric(df.get("num_intermediate_stops"), errors="coerce").fillna(0)
    keep = ["transport_mode", "route", "mode_type", "passengers", "occupancy_rate",
            "distance_km", "fare_per_passenger", "num_classes", "num_intermediate_stops"]
    logger.info("Railways loaded: %d rows", len(df))
    return df[[c for c in keep if c in df.columns]]


def _load_flights(processed_dir: Path) -> pd.DataFrame:
    path = processed_dir / "flights_clean.csv"
    if not path.exists():
        logger.warning("Flights clean not found: %s", path)
        return pd.DataFrame()
    df = pd.read_csv(path, low_memory=False)
    if "passengers" not in df.columns:
        logger.warning("No passengers column in flights — skipping anomaly detection for Air.")
        return pd.DataFrame()
    df["transport_mode"]     = "Air"
    df["distance_km"]        = pd.to_numeric(df.get("duration_minutes", 60), errors="coerce").fillna(60) * 8.5
    df["fare_per_passenger"] = pd.to_numeric(df.get("price"),       errors="coerce")
    df["passengers"]         = pd.to_numeric(df.get("passengers"),  errors="coerce")
    capacity                 = pd.to_numeric(df.get("airline_tier", 2), errors="coerce").map(
        {1: 250, 2: 160, 3: 72}
    ).fillna(160)
    df["occupancy_rate"]     = (df["passengers"] / capacity * 100).clip(upper=100)
    src = df.get("source", pd.Series(dtype=str)).astype(str).str.title()
    dst = df.get("destination", pd.Series(dtype=str)).astype(str).str.title()
    df["route"]              = src + "-" + dst
    df["mode_type"]          = df.get("airline", "Unknown").astype(str)
    # Air-specific extras
    df["num_stops"]          = pd.to_numeric(df.get("num_stops"),          errors="coerce").fillna(0)
    df["duration_minutes"]   = pd.to_numeric(df.get("duration_minutes"),   errors="coerce").fillna(0)
    keep = ["transport_mode", "route", "mode_type", "passengers", "occupancy_rate",
            "distance_km", "fare_per_passenger", "num_stops", "duration_minutes"]
    logger.info("Flights loaded: %d rows", len(df))
    return df[[c for c in keep if c in df.columns]]


def load_all(processed_dir: Path) -> pd.DataFrame:
    frames = [
        _load_apsrtc(processed_dir),
        _load_railways(processed_dir),
        _load_flights(processed_dir),
    ]
    frames = [f for f in frames if not f.empty]
    if not frames:
        raise FileNotFoundError("No processed datasets found. Run ETL first.")
    df = pd.concat(frames, ignore_index=True, sort=False)
    df = df.dropna(subset=["passengers"])
    logger.info(
        "Combined dataset: %d rows | Bus=%d  Rail=%d  Air=%d",
        len(df),
        (df["transport_mode"] == "Bus").sum(),
        (df["transport_mode"] == "Rail").sum(),
        (df["transport_mode"] == "Air").sum(),
    )
    return df


# ── Anomaly detection ─────────────────────────────────────────────────────────

def run(contamination: float = 0.05) -> pd.DataFrame:
    logger.info("=== Isolation Forest Anomaly Detection START (Bus + Rail + Air) ===")

    df = load_all(DATA_PROCESSED_DIR)

    # Use shared features only — guaranteed to exist in all 3 modes
    feature_cols = [c for c in SHARED_FEATURES if c in df.columns]
    X = df[feature_cols].fillna(0).values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    iso = IsolationForest(
        contamination=contamination,
        n_estimators=200,
        random_state=RANDOM_SEED,
        n_jobs=-1,
    )
    iso.fit(X_scaled)
    df["anomaly_score"] = iso.score_samples(X_scaled)
    df["is_anomaly"]    = (iso.predict(X_scaled) == -1).astype(int)

    n_total   = len(df)
    n_anomaly = int(df["is_anomaly"].sum())
    pct       = 100 * n_anomaly / n_total

    logger.info("Total records  : %d", n_total)
    logger.info("Anomalies found: %d (%.2f%%)", n_anomaly, pct)

    # ── Per-mode breakdown ────────────────────────────────────────────────────
    logger.info("\nAnomaly breakdown by transport mode:")
    for mode in ["Bus", "Rail", "Air"]:
        mode_df  = df[df["transport_mode"] == mode]
        mode_anom = int(mode_df["is_anomaly"].sum())
        mode_pct  = 100 * mode_anom / len(mode_df) if len(mode_df) > 0 else 0
        logger.info("  %-4s : %d anomalies / %d total (%.2f%%)", mode, mode_anom, len(mode_df), mode_pct)

    # ── Top anomalous routes ──────────────────────────────────────────────────
    if "route" in df.columns:
        route_anom = (df[df["is_anomaly"] == 1]
                      .groupby(["transport_mode", "route"]).size()
                      .sort_values(ascending=False))
        logger.info("\nTop routes with anomalies:\n%s", route_anom.head(15).to_string())

    # ── Plots ─────────────────────────────────────────────────────────────────
    mode_colors  = {"Bus": "steelblue", "Rail": "darkorange", "Air": "seagreen"}
    anom_color   = "crimson"

    fig, axes = plt.subplots(1, 2, figsize=(18, 6))

    # Scatter: passengers vs occupancy — coloured by mode, anomalies marked
    for mode, grp in df[df["is_anomaly"] == 0].groupby("transport_mode"):
        axes[0].scatter(grp["passengers"], grp["occupancy_rate"],
                        c=mode_colors.get(mode, "grey"), alpha=0.3, s=15, label=f"{mode} (Normal)")
    anom_df = df[df["is_anomaly"] == 1]
    axes[0].scatter(anom_df["passengers"], anom_df["occupancy_rate"],
                    c=anom_color, alpha=0.9, s=50, marker="x",
                    label=f"Anomaly ({n_anomaly})", zorder=5)
    axes[0].set_xlabel("Passengers")
    axes[0].set_ylabel("Occupancy Rate (%)")
    axes[0].set_title("Isolation Forest — Anomalies Across All Transport Modes",
                      fontsize=13, fontweight="bold")
    axes[0].legend(fontsize=8)

    # Bar: anomaly count by mode
    mode_counts = df[df["is_anomaly"] == 1].groupby("transport_mode").size()
    bars = axes[1].bar(
        mode_counts.index, mode_counts.values,
        color=[mode_colors.get(m, "grey") for m in mode_counts.index],
        edgecolor="black", linewidth=0.5
    )
    for bar, val in zip(bars, mode_counts.values):
        axes[1].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                     str(val), ha="center", va="bottom", fontweight="bold")
    axes[1].set_xlabel("Transport Mode")
    axes[1].set_ylabel("Anomaly Count")
    axes[1].set_title("Anomaly Count by Transport Mode", fontsize=13, fontweight="bold")

    plt.tight_layout()
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    out1 = FIGURES_DIR / "anomaly_detection.png"
    plt.savefig(out1, dpi=150)
    plt.close()
    logger.info("Saved anomaly plot -> %s", out1)

    # Second plot — top anomalous routes per mode
    fig, axes = plt.subplots(1, 3, figsize=(20, 6))
    for ax, mode in zip(axes, ["Bus", "Rail", "Air"]):
        mode_anom_routes = (df[(df["is_anomaly"] == 1) & (df["transport_mode"] == mode)]
                            .groupby("route").size().sort_values(ascending=False).head(10))
        if mode_anom_routes.empty:
            ax.text(0.5, 0.5, f"No {mode} anomalies", ha="center", va="center",
                    transform=ax.transAxes)
        else:
            ax.barh(mode_anom_routes.index, mode_anom_routes.values,
                    color=mode_colors.get(mode, "grey"), alpha=0.85)
        ax.set_title(f"Top Anomalous Routes — {mode}", fontsize=12, fontweight="bold")
        ax.set_xlabel("Anomaly Count")
    plt.tight_layout()
    out2 = FIGURES_DIR / "anomaly_by_mode.png"
    plt.savefig(out2, dpi=150)
    plt.close()
    logger.info("Saved per-mode anomaly plot -> %s", out2)

    # ── Save results ──────────────────────────────────────────────────────────
    PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)
    save_cols = ["transport_mode", "route", "mode_type",
                 "passengers", "occupancy_rate", "distance_km",
                 "fare_per_passenger", "anomaly_score", "is_anomaly"]
    out_path = PREDICTIONS_DIR / "transport_anomalies.csv"
    df[[c for c in save_cols if c in df.columns]].to_csv(out_path, index=False)
    logger.info("Anomaly results saved -> %s", out_path)

    logger.info("=== Isolation Forest Anomaly Detection END ===")
    return df


if __name__ == "__main__":
    run()
