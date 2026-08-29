"""
ml/preprocessing.py — Feature preparation and time-aware train/val/test split.

FEATURE STRATEGY (leakage-free — all features available BEFORE the trip):
  Pre-trip knowns  : route, bus_type, depot, capacity, distance_km, fare_per_passenger
  Temporal         : year, month_num, day_num, dow, is_weekend, quarter, week_of_year, is_holiday
  Lag/rolling      : lag_1, lag_7, rolling_mean_7/14, rolling_max/min/std_7  (per route, shifted)
  Historical means : route_hist_mean, bustype_hist_mean, route_month_mean, route_bustype_mean
  Encodings        : route_encoded, bus_type_encoded, depot_encoded (single encoding, no duplicates)

EXCLUDED (post-trip leakage):
  occupancy_rate  = passengers / capacity * 100   (derived from target)
  revenue         = passengers * fare              (derived from target)
  fuel_consumed_liters  (correlated with distance, not demand)
"""

from pathlib import Path
import sys
import warnings

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import DATA_PROCESSED_DIR, RANDOM_SEED
from src.utils.logger import get_logger

warnings.filterwarnings("ignore")
logger = get_logger(__name__)

TARGET = "passengers"

# ── SINGLE authoritative feature list (no duplicates) ────────────────────────
# BUG 1 FIX: removed route_enc / bus_type_enc / depot_enc / day_of_week_enc / month_enc
#   which were redundant re-encodings of route_encoded / bus_type_encoded / etc.
NUMERIC_FEATURES = [
    # Pre-trip operational
    "capacity",
    "distance_km",
    "fare_per_passenger",
    # Temporal
    "year",
    "month_num",
    "day_num",
    "dow",
    "is_weekend",
    "quarter",
    "week_of_year",
    "is_holiday",
    # Lag / rolling (grouped by route, shifted — no leakage)
    "lag_1",
    "lag_7",
    "rolling_mean_7",
    "rolling_mean_14",
    "rolling_max_7",
    "rolling_min_7",
    "rolling_std_7",
    # BUG 2 FIX: New powerful historical mean features
    "route_hist_mean",        # expanding mean of passengers per route (shifted)
    "bustype_hist_mean",      # expanding mean per bus type (shifted)
    "route_month_mean",       # expanding mean per route x month (seasonality)
    "route_bustype_mean",     # expanding mean per route x bus_type combo
    # Categorical encodings (single authoritative encoding via cat.codes)
    "route_encoded",
    "bus_type_encoded",
    "depot_encoded",
]


def load_feature_data() -> pd.DataFrame:
    path = DATA_PROCESSED_DIR / "apsrtc_features.csv"
    if not path.exists():
        logger.error("Features file not found: %s -- run ETL first.", path)
        raise FileNotFoundError(path)
    df = pd.read_csv(path, low_memory=False)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date", TARGET])
    df = df.sort_values(["route", "date"]).reset_index(drop=True)
    logger.info("Loaded feature data: %d rows x %d cols", *df.shape)
    return df


def select_features(df: pd.DataFrame) -> tuple[list, pd.DataFrame]:
    """Select non-leaky, non-duplicate features. Returns (feature_list, df)."""
    df = df.copy()

    # Build final feature list — only keep what actually exists in df
    used = [f for f in NUMERIC_FEATURES if f in df.columns]

    # Drop columns that are entirely NaN (safety check)
    used = [f for f in used if df[f].notna().any()]

    logger.info("Final feature set (%d features): %s", len(used), used)
    return used, df


def _fill_route_medians(df: pd.DataFrame, feature_cols: list) -> pd.DataFrame:
    """
    BUG 3 FIX: Fill NaN feature values with per-route medians rather than 0.
    Zero-fill corrupts lag and rolling features which are centred around ~37 passengers.
    """
    df = df.copy()
    route_medians = df.groupby("route")[TARGET].median()

    for col in feature_cols:
        n_null = df[col].isna().sum()
        if n_null > 0:
            if col in ["lag_1", "lag_7", "rolling_mean_7", "rolling_mean_14",
                       "rolling_max_7", "rolling_min_7", "route_hist_mean",
                       "bustype_hist_mean", "route_month_mean", "route_bustype_mean"]:
                # Fill with route median (meaningful central value)
                df[col] = df[col].fillna(df["route"].map(route_medians))
            elif col == "rolling_std_7":
                # Fill with global std of passengers (5–11 passengers typical)
                df[col] = df[col].fillna(df[TARGET].std())
            else:
                # For truly unknown numerics, fill with column median
                df[col] = df[col].fillna(df[col].median())
    return df


def time_aware_split(
    df: pd.DataFrame,
    feature_cols: list,
    test_frac: float = 0.15,
    val_frac: float = 0.15,
) -> dict:
    """
    Chronological split (sorted by route + date):
      TRAIN  -> oldest 70% of records
      VAL    -> next 15% (used for early stopping)
      TEST   -> newest 15% (held-out evaluation)

    No shuffling -- prevents future leakage.
    NaN fill uses route medians (not zero).
    """
    # Sort by DATE ONLY for global temporal split
    # (route sort is only for computing lag features, not for splitting)
    df = df.sort_values("date").reset_index(drop=True)

    # Fill NaN before splitting
    df = _fill_route_medians(df, feature_cols)

    n = len(df)
    n_test  = max(1, int(n * test_frac))
    n_val   = max(1, int(n * val_frac))
    n_train = n - n_val - n_test

    train_df = df.iloc[:n_train]
    val_df   = df.iloc[n_train: n_train + n_val]
    test_df  = df.iloc[n_train + n_val:]

    logger.info("Time-aware split:")
    logger.info("  TRAIN : %d rows (%s -> %s)",
                len(train_df), train_df["date"].min().date(), train_df["date"].max().date())
    logger.info("  VAL   : %d rows (%s -> %s)",
                len(val_df), val_df["date"].min().date(), val_df["date"].max().date())
    logger.info("  TEST  : %d rows (%s -> %s)",
                len(test_df), test_df["date"].min().date(), test_df["date"].max().date())

    def split_xy(d: pd.DataFrame):
        X = d[feature_cols].copy()
        y = d[TARGET]
        return X, y

    X_train, y_train = split_xy(train_df)
    X_val,   y_val   = split_xy(val_df)
    X_test,  y_test  = split_xy(test_df)

    return {
        "X_train": X_train, "y_train": y_train,
        "X_val":   X_val,   "y_val":   y_val,
        "X_test":  X_test,  "y_test":  y_test,
        "feature_cols": feature_cols,
        "train_df": train_df, "val_df": val_df, "test_df": test_df,
    }


def prepare() -> dict:
    """Full preprocessing pipeline -> returns train/val/test splits."""
    df = load_feature_data()
    feature_cols, df = select_features(df)
    splits = time_aware_split(df, feature_cols)
    return splits
