"""
etl/apsrtc.py — Preprocessing + Feature Engineering pipeline for APSRTC dataset.

ACTUAL COLUMNS (confirmed from inspection):
  bus_id, route, bus_type, depot, date (str), capacity (int), passengers (int),
  occupancy_rate (float), distance_km (float), fare_per_passenger (float),
  revenue (float), fuel_consumed_liters (float), month (str), day_of_week (str)

TARGET: passengers (integer passenger count per trip)

FEATURE ENGINEERING STRATEGY:
  All lag/rolling/historical features are computed with .shift(1) to ensure
  no future leakage — only past observations are used.
"""

import warnings
import zipfile
from pathlib import Path

import pandas as pd

from src.utils.logger import get_logger

warnings.filterwarnings("ignore")
logger = get_logger(__name__)

_HERE       = Path(__file__).resolve().parent.parent.parent
RAW_CSV     = _HERE / "data" / "raw" / "apsrtc" / "APSRTC_Transport_Data.csv"
RAW_ZIP_SRC = _HERE.parent / "apsrtc.zip"
PROCESSED   = _HERE / "data" / "processed" / "apsrtc_clean.csv"
FE_OUT      = _HERE / "data" / "processed" / "apsrtc_features.csv"

TARGET = "passengers"

INDIAN_HOLIDAYS = {
    (1, 26), (8, 15), (10, 2), (11, 1), (12, 25), (1, 1),
    (4, 14), (5, 1), (10, 24),
}


def load_raw() -> pd.DataFrame:
    if RAW_CSV.exists():
        logger.info("Loading APSRTC from: %s", RAW_CSV)
        return pd.read_csv(RAW_CSV, low_memory=False)
    elif RAW_ZIP_SRC.exists():
        logger.info("Extracting from zip: %s", RAW_ZIP_SRC)
        RAW_CSV.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(RAW_ZIP_SRC, "r") as z:
            z.extractall(RAW_CSV.parent)
        return pd.read_csv(RAW_CSV, low_memory=False)
    raise FileNotFoundError(f"APSRTC data not found at {RAW_CSV}")


def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    logger.info("Raw shape: %d x %d | Columns: %s", *df.shape, list(df.columns))

    # Normalise column names
    df.columns = [c.strip().lower().replace(" ", "_").replace("-", "_") for c in df.columns]

    # Drop duplicates
    n = len(df)
    df = df.drop_duplicates()
    logger.info("Duplicates removed: %d", n - len(df))

    # Parse date
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    nulls = df["date"].isna().sum()
    if nulls:
        logger.warning("date parse failed for %d rows -- dropping them", nulls)
        df = df.dropna(subset=["date"])

    # Ensure numeric columns
    numeric_cols = ["capacity", "passengers", "occupancy_rate", "distance_km",
                    "fare_per_passenger", "revenue", "fuel_consumed_liters"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            n_miss = df[col].isna().sum()
            if n_miss > 0:
                med = df[col].median()
                df[col] = df[col].fillna(med)
                logger.info("Filled %d missing in '%s' with median %.2f", n_miss, col, med)

    # Negative passengers not valid
    if "passengers" in df.columns:
        bad = (df["passengers"] < 0).sum()
        if bad:
            df["passengers"] = df["passengers"].clip(lower=0)
            logger.warning("Clipped %d negative passenger values to 0", bad)

    # Outlier cap for passengers (IQR x 3) — conservative cap
    if "passengers" in df.columns:
        q1, q3 = df["passengers"].quantile(0.25), df["passengers"].quantile(0.75)
        iqr = q3 - q1
        hi = q3 + 3 * iqr
        n_capped = (df["passengers"] > hi).sum()
        df["passengers"] = df["passengers"].clip(upper=hi)
        if n_capped:
            logger.info("Capped %d extreme passenger values above %.0f", n_capped, hi)

    # Normalise string columns
    for col in ["bus_type", "depot", "route", "month", "day_of_week"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.title()

    logger.info("Preprocessing complete. Shape: %d x %d", *df.shape)
    return df


def _expanding_mean_shift(series: pd.Series) -> pd.Series:
    """Per-group expanding mean with shift(1) — no leakage."""
    return series.shift(1).expanding(min_periods=1).mean()


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # ── Temporal features from date ────────────────────────────────────────────
    df["date"] = pd.to_datetime(df["date"])
    dt = df["date"]
    df["year"]         = dt.dt.year
    df["month_num"]    = dt.dt.month
    df["day_num"]      = dt.dt.day
    df["dow"]          = dt.dt.dayofweek          # 0=Mon, 6=Sun
    df["is_weekend"]   = (df["dow"] >= 5).astype(int)
    df["quarter"]      = dt.dt.quarter
    df["week_of_year"] = dt.dt.isocalendar().week.astype(int)
    df["is_holiday"]   = dt.apply(
        lambda d: int((d.month, d.day) in INDIAN_HOLIDAYS) if pd.notna(d) else 0
    )

    # ── Sort by route + date BEFORE computing any lag/rolling features ─────────
    df = df.sort_values(["route", "date"]).reset_index(drop=True)

    # ── Route-level lag and rolling features (grouped by route — NO global leakage) ──
    grp = df.groupby("route")[TARGET]

    df["lag_1"]           = grp.shift(1)
    df["lag_7"]           = grp.shift(7)
    df["rolling_mean_7"]  = grp.transform(lambda x: x.shift(1).rolling(7,  min_periods=1).mean())
    df["rolling_mean_14"] = grp.transform(lambda x: x.shift(1).rolling(14, min_periods=1).mean())
    df["rolling_max_7"]   = grp.transform(lambda x: x.shift(1).rolling(7,  min_periods=1).max())
    df["rolling_min_7"]   = grp.transform(lambda x: x.shift(1).rolling(7,  min_periods=1).min())
    # FIX BUG 3: rolling_std_7 needs min_periods=2 for std; fill NaN with route median
    df["rolling_std_7"]   = grp.transform(lambda x: x.shift(1).rolling(7, min_periods=2).std())

    # NOTE: Do NOT fill NaN lag/rolling values here.
    # route_medians computed over the full df would leak target information
    # from future/test rows into training features (Bug 3 data leakage fix).
    # NaN-filling is deferred to ml/preprocessing.py::_fill_route_medians,
    # which runs AFTER the chronological split and uses only train-set statistics.

    # ── NEW FEATURES: Powerful leakage-free historical means ─────────────────
    # All use _expanding_mean_shift (shift(1) before expanding) so no future
    # target values are ever included. NaN fills (first-row-per-group) are
    # deferred to ml/preprocessing.py::_fill_route_medians, which uses
    # train-only statistics to avoid data leakage.

    # 1. Per-route expanding historical mean (strongest predictor of route baseline)
    df["route_hist_mean"] = grp.transform(_expanding_mean_shift)

    # 2. Per bus_type expanding historical mean (bus class demand signal)
    bus_grp = df.groupby("bus_type")[TARGET]
    df["bustype_hist_mean"] = bus_grp.transform(_expanding_mean_shift)

    # 3. Per route x month historical mean (captures seasonality per route)
    route_month_grp = df.groupby(["route", "month_num"])[TARGET]
    df["route_month_mean"] = route_month_grp.transform(_expanding_mean_shift)

    # 4. Per route x bus_type historical mean (route+class combo baseline)
    route_bus_grp = df.groupby(["route", "bus_type"])[TARGET]
    df["route_bustype_mean"] = route_bus_grp.transform(_expanding_mean_shift)

    # ── Encode categoricals (single authoritative encoding via cat.codes) ───────
    df["route_encoded"]    = df["route"].astype("category").cat.codes
    df["bus_type_encoded"] = df["bus_type"].astype("category").cat.codes
    df["depot_encoded"]    = df["depot"].astype("category").cat.codes
    df["dow_encoded"]      = df["dow"]          # already numeric
    df["month_encoded"]    = df["month_num"]    # already numeric

    logger.info("Feature engineering complete. Final shape: %d x %d", *df.shape)
    return df


def run() -> pd.DataFrame:
    logger.info("=== APSRTC Pipeline START ===")
    df_raw   = load_raw()
    df_clean = preprocess(df_raw)
    df_feat  = engineer_features(df_clean)

    PROCESSED.parent.mkdir(parents=True, exist_ok=True)
    df_clean.to_csv(PROCESSED, index=False)
    df_feat.to_csv(FE_OUT, index=False)
    logger.info("Saved cleaned  -> %s", PROCESSED)
    logger.info("Saved features -> %s", FE_OUT)
    logger.info("=== APSRTC Pipeline END ===")
    return df_feat


if __name__ == "__main__":
    run()
