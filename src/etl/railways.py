"""
etl/railways.py -- Preprocessing pipeline for IRCTC Indian Railways dataset.

ACTUAL COLUMNS (confirmed from inspection):
  train_no, train_name, source_station, departure_time, arrival_time,
  distance, destination_station, days_of_week, classes, intermediate_stops

NOTE: This dataset contains train schedules, NOT passenger demand/count data.
It is used for OLAP analytics (route analysis, coverage, schedule analytics)
not for ML demand prediction.
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
PROCESSED   = _HERE / "data" / "processed" / "railways_clean.csv"


def load_raw() -> pd.DataFrame:
    if RAW_CSV.exists():
        return pd.read_csv(RAW_CSV, low_memory=False)
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
