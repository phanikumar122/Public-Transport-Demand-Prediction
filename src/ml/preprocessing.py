"""
ml/preprocessing.py — Feature preparation and time-aware train/val/test split.

DATA SOURCE: All THREE datasets combined — APSRTC (bus), IRCTC (rail), Flights (air).
A transport_mode column distinguishes each dataset in the unified feature space.

FEATURE STRATEGY (leakage-free — all features available BEFORE the trip):
  Pre-trip knowns  : transport_mode, capacity/seats, distance, fare/price
  Temporal         : year, month_num, day_num, dow, is_weekend, quarter, week_of_year, is_holiday
  Lag/rolling      : lag_1, lag_7, rolling_mean_7/14, rolling_max/min/std_7 (per route, shifted)
  Historical means : route_hist_mean, modetype_hist_mean, route_month_mean, route_modetype_mean
  Encodings        : route_encoded, mode_type_encoded, operator_encoded

EXCLUDED (post-trip leakage):
  occupancy_rate  = passengers / capacity * 100   (derived from target)
  revenue         = passengers * fare              (derived from target)
  fuel_consumed_liters  (correlated with distance, not demand)
"""

from pathlib import Path
import sys
import warnings

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import DATA_PROCESSED_DIR
from src.utils.logger import get_logger

warnings.filterwarnings("ignore")
logger = get_logger(__name__)

TARGET = "passengers"

# ── SINGLE authoritative feature list (no duplicates) ────────────────────────
# Shared across all 3 transport modes. Missing columns are filled with 0.
NUMERIC_FEATURES = [
    # Pre-trip operational
    "capacity",           # bus seats / train coaches proxy / flight seats
    "distance_km",        # route distance
    "fare_per_passenger", # ticket price (normalised from price for flights)
    # Transport mode identifier
    "transport_mode_encoded",  # 0=Bus, 1=Rail, 2=Air
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
    # Historical mean features
    "route_hist_mean",
    "modetype_hist_mean",
    "route_month_mean",
    "route_modetype_mean",
    # Categorical encodings
    "route_encoded",
    "mode_type_encoded",   # bus_type / train_type / airline tier
    "operator_encoded",    # depot / airline
]

# ── Indian holidays for date features ────────────────────────────────────────
INDIAN_HOLIDAYS = {
    (1, 26), (8, 15), (10, 2), (11, 1), (12, 25), (1, 1),
    (4, 14), (5, 1), (10, 24),
}


def _load_apsrtc(processed_dir: Path) -> pd.DataFrame:
    """Load APSRTC feature-engineered data and normalise to unified schema."""
    path = processed_dir / "apsrtc_features.csv"
    if not path.exists():
        logger.warning("APSRTC features not found: %s", path)
        return pd.DataFrame()
    df = pd.read_csv(path, low_memory=False)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date", TARGET])

    # Unified schema mappings
    df["transport_mode"]      = "Bus"
    df["transport_mode_encoded"] = 0
    df["distance_km"]         = df.get("distance_km", pd.Series(dtype=float))
    df["fare_per_passenger"]  = df.get("fare_per_passenger", pd.Series(dtype=float))
    df["capacity"]            = df.get("capacity", pd.Series(dtype=float))
    # mode_type = bus_type, operator = depot
    df["mode_type"]           = df.get("bus_type", "Unknown").astype(str)
    df["operator"]            = df.get("depot",    "Unknown").astype(str)
    # route_encoded already present from apsrtc ETL
    logger.info("APSRTC loaded: %d rows", len(df))
    return df


def _load_railways(processed_dir: Path) -> pd.DataFrame:
    """Load railways cleaned data and normalise to unified schema."""
    path = processed_dir / "railways_clean.csv"
    if not path.exists():
        logger.warning("Railways clean data not found: %s", path)
        return pd.DataFrame()
    df = pd.read_csv(path, low_memory=False)
    if TARGET not in df.columns:
        logger.warning("No 'passengers' column in railways data — skipping.")
        return pd.DataFrame()

    df = df.dropna(subset=[TARGET])

    # Railways has no date column — generate synthetic 2019-2024 dates
    # spread uniformly so time-aware split works (one record per train per day simulated)
    import numpy as np
    np.random.seed(42)
    date_range = pd.date_range("2019-01-01", "2024-12-31", freq="D")
    df["date"] = np.random.choice(date_range, size=len(df), replace=True)
    df["date"] = pd.to_datetime(df["date"])

    # Temporal features
    dt = df["date"]
    df["year"]         = dt.dt.year
    df["month_num"]    = dt.dt.month
    df["day_num"]      = dt.dt.day
    df["dow"]          = dt.dt.dayofweek
    df["is_weekend"]   = (df["dow"] >= 5).astype(int)
    df["quarter"]      = dt.dt.quarter
    df["week_of_year"] = dt.dt.isocalendar().week.astype(int)
    df["is_holiday"]   = dt.apply(
        lambda d: int((d.month, d.day) in INDIAN_HOLIDAYS) if pd.notna(d) else 0
    )

    # Unified schema mappings
    df["transport_mode"]         = "Rail"
    df["transport_mode_encoded"] = 1
    df["distance_km"]            = pd.to_numeric(df.get("distance", 500), errors="coerce").fillna(500)
    df["fare_per_passenger"]     = (df["distance_km"] * 0.5).clip(lower=30)  # approx INR/km
    df["capacity"]               = df["distance_km"].apply(
        lambda d: 800 if d > 1000 else (500 if d > 400 else 200)
    )
    df["route"]    = (df.get("source_station", "").astype(str).str.title() + "-" +
                      df.get("destination_station", "").astype(str).str.title())
    df["mode_type"]  = df.get("train_type", "Express").astype(str)
    df["operator"]   = df.get("train_name",  "Unknown").astype(str).str[:20]

    logger.info("Railways loaded: %d rows", len(df))
    return df


def _load_flights(processed_dir: Path) -> pd.DataFrame:
    """Load flights cleaned data and normalise to unified schema."""
    path = processed_dir / "flights_clean.csv"
    if not path.exists():
        logger.warning("Flights clean data not found: %s", path)
        return pd.DataFrame()
    df = pd.read_csv(path, low_memory=False)
    if TARGET not in df.columns:
        logger.warning("No 'passengers' column in flights data — skipping.")
        return pd.DataFrame()

    df["date_of_journey"] = pd.to_datetime(df.get("date_of_journey"), errors="coerce")
    df = df.dropna(subset=[TARGET, "date_of_journey"])
    df["date"] = df["date_of_journey"]

    # Temporal (may already exist from ETL, but re-derive to be safe)
    dt = df["date"]
    df["year"]         = dt.dt.year
    df["month_num"]    = dt.dt.month
    df["day_num"]      = dt.dt.day
    df["dow"]          = dt.dt.dayofweek
    df["is_weekend"]   = (df["dow"] >= 5).astype(int)
    df["quarter"]      = dt.dt.quarter
    df["week_of_year"] = dt.dt.isocalendar().week.astype(int)
    df["is_holiday"]   = dt.apply(
        lambda d: int((d.month, d.day) in INDIAN_HOLIDAYS) if pd.notna(d) else 0
    )

    # Unified schema mappings
    df["transport_mode"]         = "Air"
    df["transport_mode_encoded"] = 2
    df["distance_km"]            = pd.to_numeric(
        df.get("duration_minutes", 60), errors="coerce").fillna(60) * 8.5  # ~8.5 km/min for domestic
    df["fare_per_passenger"]     = pd.to_numeric(df.get("price", 5000), errors="coerce").fillna(5000)
    df["capacity"]               = pd.to_numeric(df.get("airline_tier", 2), errors="coerce").map(
        {1: 250, 2: 160, 3: 72}
    ).fillna(160)
    df["route"]      = (df.get("source", "").astype(str).str.title() + "-" +
                        df.get("destination", "").astype(str).str.title())
    df["mode_type"]  = df.get("airline", "Unknown").astype(str)
    df["operator"]   = df.get("airline", "Unknown").astype(str)

    logger.info("Flights loaded: %d rows", len(df))
    return df


def _expanding_mean_shift(series: pd.Series) -> pd.Series:
    """Per-group expanding mean with shift(1) — no leakage."""
    return series.shift(1).expanding(min_periods=1).mean()


def _engineer_shared_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build lag/rolling/historical features on the unified dataset.
    All features use shift(1) so no future target values are included.
    """
    df = df.sort_values(["route", "date"]).reset_index(drop=True)

    grp = df.groupby("route")[TARGET]

    df["lag_1"]           = grp.shift(1)
    df["lag_7"]           = grp.shift(7)
    df["rolling_mean_7"]  = grp.transform(lambda x: x.shift(1).rolling(7,  min_periods=1).mean())
    df["rolling_mean_14"] = grp.transform(lambda x: x.shift(1).rolling(14, min_periods=1).mean())
    df["rolling_max_7"]   = grp.transform(lambda x: x.shift(1).rolling(7,  min_periods=1).max())
    df["rolling_min_7"]   = grp.transform(lambda x: x.shift(1).rolling(7,  min_periods=1).min())
    df["rolling_std_7"]   = grp.transform(lambda x: x.shift(1).rolling(7,  min_periods=2).std())

    # Historical means (leakage-free)
    df["route_hist_mean"]    = grp.transform(_expanding_mean_shift)
    mode_grp = df.groupby("mode_type")[TARGET]
    df["modetype_hist_mean"] = mode_grp.transform(_expanding_mean_shift)
    route_month_grp = df.groupby(["route", "month_num"])[TARGET]
    df["route_month_mean"]   = route_month_grp.transform(_expanding_mean_shift)
    route_mode_grp = df.groupby(["route", "mode_type"])[TARGET]
    df["route_modetype_mean"] = route_mode_grp.transform(_expanding_mean_shift)

    # Categorical encodings (unified across all modes)
    df["route_encoded"]      = df["route"].astype("category").cat.codes
    df["mode_type_encoded"]  = df["mode_type"].astype("category").cat.codes
    df["operator_encoded"]   = df["operator"].astype("category").cat.codes

    return df


def load_feature_data() -> pd.DataFrame:
    """Load and merge all 3 processed datasets into a unified feature DataFrame."""
    frames = [
        _load_apsrtc(DATA_PROCESSED_DIR),
        _load_railways(DATA_PROCESSED_DIR),
        _load_flights(DATA_PROCESSED_DIR),
    ]
    frames = [f for f in frames if not f.empty]
    if not frames:
        raise FileNotFoundError("No processed datasets found. Run ETL first.")

    # Concatenate — missing columns filled with NaN
    df = pd.concat(frames, ignore_index=True, sort=False)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date", TARGET])
    df[TARGET] = pd.to_numeric(df[TARGET], errors="coerce")
    df = df.dropna(subset=[TARGET])
    df = df.sort_values(["route", "date"]).reset_index(drop=True)

    # Ensure core columns exist
    for col in ["distance_km", "fare_per_passenger", "capacity"]:
        df[col] = pd.to_numeric(df.get(col), errors="coerce").fillna(df.get(col, pd.Series()).median() or 0)

    # Build shared lag/rolling/encoding features
    df = _engineer_shared_features(df)

    logger.info(
        "Combined dataset: %d rows | Bus=%d  Rail=%d  Air=%d",
        len(df),
        (df["transport_mode"] == "Bus").sum(),
        (df["transport_mode"] == "Rail").sum(),
        (df["transport_mode"] == "Air").sum(),
    )
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

def _fill_route_medians(
    df: pd.DataFrame,
    feature_cols: list,
    train_route_medians: pd.Series,
    train_global_std: float,
    train_global_median: float = 0.0,
) -> pd.DataFrame:
    """
    Fill NaN feature values using statistics derived exclusively from the
    TRAINING partition (passed in as parameters) to prevent data leakage.

    - lag/rolling/hist_mean features -> per-route median from training data, fallback to global median
    - rolling_std_7                  -> global std of passengers from training data
    - other numeric features         -> column median or global median
    """
    df = df.copy()

    lag_rolling_cols = [
        "lag_1", "lag_7", "rolling_mean_7", "rolling_mean_14",
        "rolling_max_7", "rolling_min_7",
        "route_hist_mean", "modetype_hist_mean",
        "route_month_mean", "route_modetype_mean",
    ]

    for col in feature_cols:
        if col in lag_rolling_cols:
            df[col] = df[col].fillna(df["route"].map(train_route_medians)).fillna(train_global_median).fillna(0)
        elif col == "rolling_std_7":
            df[col] = df[col].fillna(train_global_std).fillna(0)
        else:
            col_med = df[col].median()
            df[col] = df[col].fillna(col_med if pd.notna(col_med) else train_global_median).fillna(0)

    # Absolute fallback guarantees 0 NaNs
    df[feature_cols] = df[feature_cols].fillna(0)
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
    NaN fill uses route medians derived from TRAINING data only (Bug 3 fix).
    """
    # Sort by DATE ONLY for global temporal split
    # (route sort is only for computing lag features, not for splitting)
    df = df.sort_values("date").reset_index(drop=True)

    n = len(df)
    n_test  = max(1, int(n * test_frac))
    n_val   = max(1, int(n * val_frac))
    n_train = n - n_val - n_test

    train_df = df.iloc[:n_train].copy()
    val_df   = df.iloc[n_train: n_train + n_val].copy()
    test_df  = df.iloc[n_train + n_val:].copy()

    # Compute fill statistics exclusively from the TRAINING partition
    # so no future information leaks into val/test NaN fills.
    train_route_medians = train_df.groupby("route")[TARGET].median()
    train_global_std    = float(train_df[TARGET].std())
    train_global_median = float(train_df[TARGET].median())

    train_df = _fill_route_medians(train_df, feature_cols, train_route_medians, train_global_std, train_global_median)
    val_df   = _fill_route_medians(val_df,   feature_cols, train_route_medians, train_global_std, train_global_median)
    test_df  = _fill_route_medians(test_df,  feature_cols, train_route_medians, train_global_std, train_global_median)

    logger.info("Time-aware split:")
    logger.info("  TRAIN : %d rows (%s -> %s)",
                len(train_df), train_df["date"].min().date(), train_df["date"].max().date())
    logger.info("  VAL   : %d rows (%s -> %s)",
                len(val_df), val_df["date"].min().date(), val_df["date"].max().date())
    logger.info("  TEST  : %d rows (%s -> %s)",
                len(test_df), test_df["date"].min().date(), test_df["date"].max().date())
    if "transport_mode" in df.columns:
        for mode in ["Bus", "Rail", "Air"]:
            cnt = (df["transport_mode"] == mode).sum()
            logger.info("  %-5s : %d rows total", mode, cnt)

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
    """Full preprocessing pipeline -> loads all 3 datasets, returns train/val/test splits."""
    df = load_feature_data()
    feature_cols, df = select_features(df)
    splits = time_aware_split(df, feature_cols)
    return splits
