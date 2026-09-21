"""
etl/railways.py -- Preprocessing pipeline for IRCTC Indian Railways dataset.

ACTUAL COLUMNS (confirmed from inspection):
  train_no, train_name, source_station, departure_time, arrival_time,
  distance, destination_station, days_of_week, classes, intermediate_stops,
  passengers (seeded based on train type + distance)

NOTE: passengers column has been seeded with realistic values derived from
train type (Rajdhani/Shatabdi/Express/Local) and route distance. It is used
for both OLAP analytics and ML demand prediction alongside APSRTC and Flights.
"""

import warnings
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from src.utils.logger import get_logger

warnings.filterwarnings("ignore")
logger = get_logger(__name__)

_HERE       = Path(__file__).resolve().parent.parent.parent
RAW_CSV     = _HERE / "data" / "raw" / "railways" / "IRCTC_cleaned.csv"
RAW_ZIP_SRC = _HERE.parent / "irctc.zip"
DATASETS_CSV = _HERE / "datasets" / "Irctc.csv"   # fallback: datasets/ folder
PROCESSED   = _HERE / "data" / "processed" / "railways_clean.csv"


def load_raw() -> pd.DataFrame:
    if RAW_CSV.exists():
        return pd.read_csv(RAW_CSV, low_memory=False)
    elif DATASETS_CSV.exists():
        logger.info("Loading railways from datasets/ folder: %s", DATASETS_CSV)
        return pd.read_csv(DATASETS_CSV, low_memory=False)
    elif RAW_ZIP_SRC.exists():
        RAW_CSV.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(RAW_ZIP_SRC, "r") as z:
            z.extractall(RAW_CSV.parent)
        return pd.read_csv(RAW_CSV, low_memory=False)
    raise FileNotFoundError(f"Railways data not found. Place IRCTC_cleaned.csv in {RAW_CSV.parent}")


def _parse_time_to_minutes(t: str) -> float:
    """Convert 'HH:MM' or 'H:MM' to total minutes from midnight."""
    try:
        parts = str(t).strip().split(":")
        return int(parts[0]) * 60 + int(parts[1])
    except Exception:
        return np.nan


def _parse_classes(c: str) -> dict:
    """Return dict of class flags from comma-separated class string."""
    classes = [x.strip() for x in str(c).split(",")]
    return {
        "has_1A": int("1A" in classes),
        "has_2A": int("2A" in classes),
        "has_3A": int("3A" in classes),
        "has_SL": int("SL" in classes),
        "has_GN": int("GN" in classes),
        "num_classes": len(classes),
    }


def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    logger.info("Railways shape: %d x %d | Cols: %s", *df.shape, list(df.columns))

    # Duplicates
    n = len(df)
    df = df.drop_duplicates()
    logger.info("Duplicates removed: %d", n - len(df))

    # Handle missing classes
    df["classes"] = df["classes"].fillna("GN")

    # ── Passengers column ─────────────────────────────────────────────────────
    if "passengers" in df.columns:
        df["passengers"] = pd.to_numeric(df["passengers"], errors="coerce")
        n_miss = df["passengers"].isna().sum()
        if n_miss:
            df["passengers"] = df["passengers"].fillna(df["passengers"].median())
            logger.info("Filled %d missing passenger values with median", n_miss)
        df["passengers"] = df["passengers"].clip(lower=0).astype(int)
        logger.info("passengers: min=%d  max=%d  mean=%.1f",
                    df["passengers"].min(), df["passengers"].max(), df["passengers"].mean())
    else:
        logger.warning("No 'passengers' column found in railways data.")

    # Parse time fields to minutes
    df["dep_minutes"]  = df["departure_time"].apply(_parse_time_to_minutes)
    df["arr_minutes"]  = df["arrival_time"].apply(_parse_time_to_minutes)

    # Distance
    df["distance"] = pd.to_numeric(df["distance"], errors="coerce")
    df["distance"] = df["distance"].fillna(df["distance"].median())

    # Count intermediate stops
    df["num_intermediate_stops"] = df["intermediate_stops"].apply(
        lambda s: len(str(s).split("|")) - 1 if pd.notna(s) and str(s).strip() else 0
    )

    # Class expansion
    class_rows = df["classes"].apply(_parse_classes)
    class_df   = pd.DataFrame(list(class_rows), index=df.index)
    df = pd.concat([df, class_df], axis=1)

    # Days of week flags
    for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
        df[f"runs_{day.lower()}"] = df["days_of_week"].apply(
            lambda s: int(day.lower() in str(s).lower())
        )

    # Normalise strings
    for col in ["train_name", "source_station", "destination_station"]:
        df[col] = df[col].astype(str).str.strip().str.title()

    # Estimate journey duration in minutes (handles overnight trains)
    def journey_duration(row):
        d = row["dep_minutes"]
        a = row["arr_minutes"]
        if pd.isna(d) or pd.isna(a):
            return np.nan
        dur = a - d
        if dur < 0:
            dur += 24 * 60   # overnight
        return dur

    df["duration_minutes"] = df.apply(journey_duration, axis=1)

    # ── Train type classification (for ML feature engineering) ───────────────
    def classify_train(name: str) -> str:
        n = str(name).upper()
        if "RAJDHANI" in n:             return "Rajdhani"
        if "SHATABDI" in n:             return "Shatabdi"
        if "DURONTO" in n:              return "Duronto"
        if "GARIB RATH" in n:           return "Garib_Rath"
        if "SUPERFAST" in n or "SF " in n: return "Superfast"
        if "INTERCITY" in n:            return "Intercity"
        if any(x in n for x in ["PASSENGER", "MEMU", "DMU", "EMU", "PASS"]):
            return "Local"
        return "Express"

    df["train_type"] = df["train_name"].apply(classify_train)
    df["train_type_encoded"] = df["train_type"].astype("category").cat.codes

    # ── Temporal features (from days_of_week) ─────────────────────────────────
    df["runs_weekday"] = df["days_of_week"].apply(
        lambda s: int(any(d in str(s).upper() for d in ["MON", "TUE", "WED", "THU", "FRI"]))
    )
    df["runs_weekend"] = df["days_of_week"].apply(
        lambda s: int(any(d in str(s).upper() for d in ["SAT", "SUN"]))
    )
    df["runs_daily"] = df["days_of_week"].apply(
        lambda s: int(all(d in str(s).upper() for d in ["MON","TUE","WED","THU","FRI","SAT","SUN"]))
    )

    logger.info("Railways preprocessing complete. Shape: %d x %d", *df.shape)
    return df


def run() -> pd.DataFrame:
    logger.info("=== Railways Pipeline START ===")
    df = preprocess(load_raw())
    PROCESSED.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(PROCESSED, index=False)
    logger.info("Saved -> %s", PROCESSED)
    logger.info("=== Railways Pipeline END ===")
    return df


if __name__ == "__main__":
    run()
