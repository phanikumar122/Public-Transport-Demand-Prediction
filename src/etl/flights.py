"""
etl/flights.py -- Preprocessing pipeline for Indian Domestic Flights dataset.

Actual columns: index, airline, date_of_journey, Source, destination, route,
                dep_time, Arrival_time, Duration, Total_stops, Additional_info,
                Price, passengers (seeded based on airline capacity + stops load factor + price)

NOTE: passengers column has been seeded with realistic values derived from
airline fleet capacity tier, number of stops (load factor proxy), and ticket
price. Used for ML demand prediction alongside APSRTC and IRCTC datasets.
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
RAW_ZIP     = _HERE / "data" / "raw" / "flights" / "flights.csv"
RAW_ZIP_SRC = _HERE.parent / "domestic flights.zip"
DATASETS_CSV = _HERE / "datasets" / "flights.csv"   # fallback: datasets/ folder
PROCESSED   = _HERE / "data" / "processed" / "flights_clean.csv"


def load_raw() -> pd.DataFrame:
    if RAW_ZIP.exists():
        return pd.read_csv(RAW_ZIP, low_memory=False)
    elif DATASETS_CSV.exists():
        logger.info("Loading flights from datasets/ folder: %s", DATASETS_CSV)
        return pd.read_csv(DATASETS_CSV, low_memory=False)
    elif RAW_ZIP_SRC.exists():
        RAW_ZIP.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(RAW_ZIP_SRC, "r") as z:
            z.extractall(RAW_ZIP.parent)
        return pd.read_csv(RAW_ZIP, low_memory=False)
    raise FileNotFoundError(f"Flights data not found. Place flights.csv in {RAW_ZIP.parent}")


def _parse_duration(s: str) -> float:
    """Convert '2h 30min' or '1h 0min' to minutes."""
    try:
        s = str(s).lower().strip()
        hours, mins = 0, 0
        if "h" in s:
            parts = s.split("h")
            hours = int(parts[0].strip())
            mins_part = parts[1].replace("min", "").strip()
            mins = int(mins_part) if mins_part else 0
        elif "min" in s:
            mins = int(s.replace("min", "").strip())
        return hours * 60 + mins
    except Exception:
        return np.nan


def _parse_stops(s: str) -> int:
    """Convert 'non-stop', '1 stop', '2 stops' to integer."""
    s = str(s).lower().strip()
    if "non" in s:
        return 0
    try:
        return int(s.split()[0])
    except Exception:
        return 0


def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Normalise column names
    df.columns = [c.strip().replace(" ", "_").lower() for c in df.columns]
    df = df.drop(columns=["index"], errors="ignore")

    logger.info("Flights shape: %d x %d", *df.shape)

    # Duplicates
    n = len(df)
    df = df.drop_duplicates()
    logger.info("Duplicates removed: %d", n - len(df))

    # Parse date
    df["date_of_journey"] = pd.to_datetime(df["date_of_journey"], errors="coerce")
    logger.info("date_of_journey parsed. Nulls: %d", df["date_of_journey"].isna().sum())

    # Parse times -- dep_time, arrival_time
    for col in ["dep_time", "arrival_time"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], format="%H:%M", errors="coerce").dt.time

    # Duration in minutes
    df["duration_minutes"] = df["duration"].apply(_parse_duration)
    logger.info("duration_minutes created. Nulls: %d", df["duration_minutes"].isna().sum())
    df["duration_minutes"].fillna(df["duration_minutes"].median(), inplace=True)

    # Parse stops
    df["num_stops"] = df["total_stops"].apply(_parse_stops)

    # Normalise categoricals
    for col in ["airline", "source", "destination", "additional_info"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.title()

    # Temporal features
    dt = df["date_of_journey"]
    df["year"]        = dt.dt.year
    df["month"]       = dt.dt.month
    df["day"]         = dt.dt.day
    df["day_of_week"] = dt.dt.dayofweek
    df["quarter"]     = dt.dt.quarter
    df["is_weekend"]  = (dt.dt.dayofweek >= 5).astype(int)

    # Price outlier cap
    q1, q3 = df["price"].quantile(0.25), df["price"].quantile(0.75)
    iqr = q3 - q1
    df["price"] = df["price"].clip(q1 - 3 * iqr, q3 + 3 * iqr)

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
        logger.warning("No 'passengers' column found in flights data.")

    # ── Airline tier encoding (for ML) ────────────────────────────────────────
    # Tier 1 = full-service (Air India, Vistara), Tier 2 = LCC (IndiGo, SpiceJet),
    # Tier 3 = regional (TruJet, Star Air, Alliance Air)
    AIRLINE_TIER = {
        "Air India": 1, "Vistara": 1,
        "Indigo": 2, "Spicejet": 2, "Goair": 2, "Akasa Air": 2, "Airasia India": 2,
        "Alliance Air": 3, "Trujet": 3, "Star Air": 3,
    }
    if "airline" in df.columns:
        df["airline_tier"] = df["airline"].str.title().map(AIRLINE_TIER).fillna(2).astype(int)
        df["airline_encoded"] = df["airline"].astype("category").cat.codes

    # ── Route-level features ──────────────────────────────────────────────────
    if "source" in df.columns and "destination" in df.columns:
        df["route_pair"] = df["source"].str.title() + "-" + df["destination"].str.title()
        df["route_encoded"] = df["route_pair"].astype("category").cat.codes

    logger.info("Flights preprocessing complete. Shape: %d x %d", *df.shape)
    return df


def run() -> pd.DataFrame:
    logger.info("=== Flights Pipeline START ===")
    df = preprocess(load_raw())
    PROCESSED.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(PROCESSED, index=False)
    logger.info("Saved -> %s", PROCESSED)
    logger.info("=== Flights Pipeline END ===")
    return df


if __name__ == "__main__":
    run()
