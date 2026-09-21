"""
ml/predict.py — Reusable prediction pipeline.

Input : route, date, bus_type, distance_km, capacity, fare_per_passenger, is_holiday
Output: predicted_passenger_demand, demand_category, recommended_buses

Also generates batch predictions on all splits and saves to:
  - outputs/predictions/demand_predictions.csv
  - MySQL fact_predictions table (via load.py, optional)
"""

import math
import json
import warnings
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import joblib

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import MODELS_DIR, PREDICTIONS_DIR
from src.ml.preprocessing import prepare, select_features, load_feature_data
from src.utils.logger import get_logger

warnings.filterwarnings("ignore")
logger = get_logger(__name__)

INDIAN_HOLIDAYS = {
    (1, 26), (8, 15), (10, 2), (11, 1), (12, 25), (1, 1),
    (4, 14), (5, 1), (10, 24),
}


def calibrate_thresholds(df: pd.DataFrame) -> tuple[float, float]:
    """Set demand thresholds from 33rd/66th percentile of training target."""
    s = pd.to_numeric(df["passengers"], errors="coerce").dropna()
    p33 = float(s.quantile(0.33)) if len(s) > 0 else 30.0
    p66 = float(s.quantile(0.66)) if len(s) > 0 else 50.0
    logger.info("Demand thresholds -- Low < %.0f  |  High > %.0f", p33, p66)
    return p33, p66


def demand_category(val: float, low: float, high: float) -> str:
    val_f, low_f, high_f = float(val), float(low), float(high)
    if val_f < low_f:
        return "Low"
    elif val_f > high_f:
        return "High"
    return "Medium"


def load_best_model():
    path = MODELS_DIR / "best_model.pkl"
    if not path.exists():
        raise FileNotFoundError(f"No trained model at {path}. Run train.py first.")
    return joblib.load(path)


def _build_row_dict(
    route: str,
    dt: pd.Timestamp,
    bus_type: str,
    distance_km: float,
    capacity: int,
    fare_per_passenger: float,
    is_holiday: int,
    df_hist: pd.DataFrame,
    feature_cols: list,
    depot: str = "",
) -> dict:
    """
    BUG 5 FIX: Build a complete feature row including all new historical mean features.
    Uses actual historical data for lag/rolling/hist_mean features (route median fallback).
    """
    # Route-specific history
    route_hist = df_hist[df_hist["route"] == route]["passengers"]
    bus_hist   = df_hist[df_hist["bus_type"] == bus_type]["passengers"]
    route_bus_hist = df_hist[
        (df_hist["route"] == route) & (df_hist["bus_type"] == bus_type)
    ]["passengers"]
    route_month_hist = df_hist[
        (df_hist["route"] == route) & (df_hist["month_num"] == dt.month)
    ]["passengers"]

    # Global fallback
    global_median = df_hist["passengers"].median()

    lag_1 = route_hist.iloc[-1]          if len(route_hist) >= 1 else global_median
    lag_7 = route_hist.iloc[-7]          if len(route_hist) >= 7 else global_median
    roll7  = route_hist.tail(7).mean()   if len(route_hist) >= 1 else global_median
    roll14 = route_hist.tail(14).mean()  if len(route_hist) >= 1 else global_median
    rmax7  = route_hist.tail(7).max()    if len(route_hist) >= 1 else global_median
    rmin7  = route_hist.tail(7).min()    if len(route_hist) >= 1 else global_median
    rstd7  = route_hist.tail(7).std()    if len(route_hist) >= 2 else df_hist["passengers"].std()

    route_hist_mean   = route_hist.mean()            if len(route_hist) >= 1 else global_median
    bustype_hist_mean = bus_hist.mean()              if len(bus_hist) >= 1 else global_median
    route_month_mean  = route_month_hist.mean()      if len(route_month_hist) >= 1 else route_hist_mean
    route_bustype_mean = route_bus_hist.mean()       if len(route_bus_hist) >= 1 else route_hist_mean

    # Categorical encodings — map from training data categories safely
    route_vals   = [str(x) for x in df_hist["route"].dropna().unique()]
    route_cats   = dict(enumerate(sorted(route_vals)))
    route_inv    = {v: k for k, v in route_cats.items()}

    bustype_col  = df_hist["bus_type"] if "bus_type" in df_hist.columns else pd.Series(dtype=object)
    bustype_vals = [str(x) for x in bustype_col.dropna().unique()]
    bustype_cats = dict(enumerate(sorted(bustype_vals)))
    bustype_inv  = {v: k for k, v in bustype_cats.items()}

    depot_col    = df_hist["depot"] if "depot" in df_hist.columns else pd.Series(dtype=object)
    depot_vals   = [str(x) for x in depot_col.dropna().unique()]
    depot_cats   = dict(enumerate(sorted(depot_vals)))
    depot_inv    = {v: k for k, v in depot_cats.items()}

    row = {
        "capacity":             capacity,
        "distance_km":          distance_km,
        "fare_per_passenger":   fare_per_passenger,
        "year":                 dt.year,
        "month_num":            dt.month,
        "day_num":              dt.day,
        "dow":                  dt.dayofweek,
        "is_weekend":           int(dt.dayofweek >= 5),
        "quarter":              dt.quarter,
        "week_of_year":         int(dt.isocalendar().week),
        "is_holiday":           is_holiday,
        "lag_1":                lag_1,
        "lag_7":                lag_7,
        "rolling_mean_7":       roll7,
        "rolling_mean_14":      roll14,
        "rolling_max_7":        rmax7,
        "rolling_min_7":        rmin7,
        "rolling_std_7":        rstd7,
        "route_hist_mean":      route_hist_mean,
        "bustype_hist_mean":    bustype_hist_mean,
        "route_month_mean":     route_month_mean,
        "route_bustype_mean":   route_bustype_mean,
        "route_encoded":        route_inv.get(route, 0),
        "bus_type_encoded":     bustype_inv.get(bus_type, 0),
        # Use the depot-to-code mapping from training data (Bug 7 fix — was hardcoded 0)
        "depot_encoded":        depot_inv.get(depot, 0),
        "dow_encoded":          dt.dayofweek,
        "month_encoded":        dt.month,
    }
    return row


def predict_single(
    route: str,
    date: str,
    bus_type: str,
    distance_km: float,
    capacity: int = 49,
    fare_per_passenger: float = 100.0,
    is_holiday: int = 0,
    bus_capacity: int = 50,
    depot: str = "",
) -> dict:
    """
    Predict demand for a single trip.

    Returns:
        predicted_demand : int
        demand_category  : str (Low / Medium / High)
        recommended_buses: int
    """
    model = load_best_model()
    df_full = load_feature_data()
    low_thr, high_thr = calibrate_thresholds(df_full)

    # Load feature list from saved metadata
    meta_path = MODELS_DIR / "model_metadata.json"
    if meta_path.exists():
        with open(meta_path) as f:
            meta = json.load(f)
        feature_cols = meta["features"]
    else:
        feature_cols, _ = select_features(df_full)

    dt = pd.to_datetime(date)
    row = _build_row_dict(
        route, dt, bus_type, distance_km, capacity, fare_per_passenger,
        is_holiday, df_full, feature_cols, depot=depot
    )

    X = pd.DataFrame([row])
    # Ensure all required features are present
    for f in feature_cols:
        if f not in X.columns:
            X[f] = 0.0

    pred = float(np.clip(model.predict(X[feature_cols])[0], 0, capacity * 1.1))
    pred_int = int(round(pred))
    cat  = demand_category(pred_int, low_thr, high_thr)
    buses = math.ceil(pred_int / bus_capacity) if bus_capacity > 0 else 1

    result = {
        "route":                route,
        "date":                 date,
        "bus_type":             bus_type,
        "distance_km":          distance_km,
        "predicted_demand":     pred_int,
        "demand_category":      cat,
        "recommended_buses":    buses,
        "bus_capacity_assumed": bus_capacity,
        "model_name":           type(model).__name__,
    }

    logger.info(
        "Prediction | Route: %-25s | Date: %s | Predicted: %d passengers | "
        "Category: %-6s | Buses: %d",
        route, date, pred_int, cat, buses
    )
    return result


def generate_batch_predictions(bus_capacity: int = 50) -> pd.DataFrame:
    """
    Generate predictions for the entire APSRTC dataset.
    Returns a prediction DataFrame ready for analysis and reporting.
    """
    logger.info("Generating batch predictions...")
    model = load_best_model()
    splits = prepare()

    df_full  = load_feature_data()
    low_thr, high_thr = calibrate_thresholds(df_full)

    records = []
    prediction_id = 1

    for split_name, (X, y, df_part) in [
        ("train", (splits["X_train"], splits["y_train"], splits["train_df"])),
        ("val",   (splits["X_val"],   splits["y_val"],   splits["val_df"])),
        ("test",  (splits["X_test"],  splits["y_test"],  splits["test_df"])),
    ]:
        preds = np.clip(model.predict(X), 0, None)

        for i, (pred, actual) in enumerate(zip(preds, y)):
            row       = df_part.iloc[i]
            pred_int  = int(round(pred))
            actual_int = int(actual)
            cat   = demand_category(pred_int, low_thr, high_thr)
            buses = math.ceil(pred_int / bus_capacity) if bus_capacity > 0 else 1
            err   = actual_int - pred_int

            date_val = row.get("date", None)
            date_key = int(pd.to_datetime(date_val).strftime("%Y%m%d")) if pd.notna(date_val) else 20240101

            records.append({
                "prediction_id":     prediction_id,
                "date":              str(date_val)[:10] if pd.notna(date_val) else None,
                "date_key":          date_key,
                "route":             str(row.get("route", "")),
                "bus_type":          str(row.get("bus_type", "")),
                "transport_mode":    "Bus",
                "actual_demand":     actual_int,
                "predicted_demand":  pred_int,
                "demand_category":   cat,
                "prediction_error":  err,
                "recommended_buses": buses,
                "bus_capacity_used": bus_capacity,
                "model_name":        type(model).__name__,
                "split":             split_name,
            })
            prediction_id += 1

    pred_df = pd.DataFrame(records)
    PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PREDICTIONS_DIR / "demand_predictions.csv"
    pred_df.to_csv(out_path, index=False)
    logger.info("Batch predictions saved -> %s (%d rows)", out_path, len(pred_df))
    return pred_df


def load_predictions_to_db(pred_df: pd.DataFrame):
    """Load prediction results into MySQL fact_predictions table."""
    try:
        from sqlalchemy import create_engine
        from src.config import DATABASE_URL
        from src.warehouse.load import _get_route_keys

        engine = create_engine(DATABASE_URL)
        route_keys = _get_route_keys(engine)
        with engine.connect() as conn:
            from sqlalchemy import text
            mk_row = conn.execute(
                text("SELECT mode_key FROM dim_transport_mode WHERE mode_name='Bus' LIMIT 1")
            ).fetchone()
        mk = mk_row[0] if mk_row else 1

        db_df = pred_df.copy()
        db_df["route_key"] = db_df["route"].map(route_keys).fillna(1).astype(int)
        db_df["mode_key"]  = mk

        cols = ["date_key", "route_key", "mode_key", "actual_demand", "predicted_demand",
                "demand_category", "model_name", "prediction_error", "recommended_buses", "bus_capacity_used"]
        db_df[cols].to_sql(
            "fact_predictions", con=engine, if_exists="append",
            index=False, method="multi", chunksize=200
        )
        logger.info("Predictions loaded to MySQL fact_predictions table.")
    except Exception as e:
        logger.warning("Could not load predictions to DB: %s", e)


def run(bus_capacity: int = 50, load_db: bool = False) -> pd.DataFrame:
    logger.info("=== Prediction Pipeline START ===")

    # Demo single prediction
    demo = predict_single(
        route="Kurnool-Hyderabad",
        date="2024-12-15",
        bus_type="Volvo Ac",
        distance_km=326.0,
        capacity=49,
        fare_per_passenger=908.75,
        is_holiday=0,
        bus_capacity=bus_capacity,
    )
    logger.info("Demo prediction: %s", demo)

    # Batch predictions
    pred_df = generate_batch_predictions(bus_capacity)

    if load_db:
        load_predictions_to_db(pred_df)

    logger.info("=== Prediction Pipeline END ===")
    return pred_df


if __name__ == "__main__":
    run()
