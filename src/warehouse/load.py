"""
warehouse/load.py -- Load cleaned/processed data into MySQL data warehouse.

Populates:
  - dim_date
  - dim_route
  - dim_transport_mode
  - dim_location
  - fact_transport  (from APSRTC, Flights, Railways)
  - fact_predictions (from batch ML predictions)

Usage:
    python -m src.warehouse.load
"""

import sys
from pathlib import Path
from datetime import date

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.config import DATABASE_URL, DATA_PROCESSED_DIR
from src.utils.logger import get_logger

logger = get_logger(__name__)


# --- Engine -------------------------------------------------------------------

def get_engine():
    try:
        engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection established.")
        return engine
    except Exception as e:
        logger.error("Cannot connect to database: %s", e)
        logger.error("Please ensure MySQL is running and credentials in .env are correct.")
        raise


# --- Schema creation ----------------------------------------------------------

def create_schema(engine):
    schema_path = Path(__file__).parent / "schema.sql"
    if not schema_path.exists():
        logger.error("schema.sql not found at %s", schema_path)
        return

    sql_content = schema_path.read_text(encoding="utf-8")
    
    # Strip comment lines before splitting into SQL statements
    clean_lines = []
    for line in sql_content.splitlines():
        trimmed = line.strip()
        if trimmed.startswith("--") or not trimmed:
            continue
        clean_lines.append(line)

    clean_sql = "\n".join(clean_lines)
    statements = [s.strip() for s in clean_sql.split(";") if s.strip()]

    with engine.connect() as conn:
        for stmt in statements:
            try:
                conn.execute(text(stmt))
                conn.commit()
            except Exception as e:
                err_msg = str(e).lower()
                if "already exists" not in err_msg and "table" not in err_msg:
                    logger.warning("Schema stmt warning: %s", e)
    logger.info("Schema applied successfully.")


# --- DIM_DATE population ------------------------------------------------------

# Holiday set used to populate dim_date.is_holiday.
# Must stay in sync with INDIAN_HOLIDAYS in src/etl/apsrtc.py and src/ml/predict.py.
HOLIDAYS = {
    date(y, m, d)
    for y in range(2019, 2026)
    for (m, d) in [
        (1, 26),   # Republic Day
        (8, 15),   # Independence Day
        (10, 2),   # Gandhi Jayanti
        (11, 1),   # Andhra Pradesh Statehood Day
        (12, 25),  # Christmas
        (1, 1),    # New Year
        (5, 1),    # Labour Day
        (4, 14),   # Ambedkar Jayanti
        (10, 24),  # Diwali (approximate fixed date used across modules)
    ]
}

HOLIDAY_NAMES = {
    (1, 26):  "Republic Day",
    (8, 15):  "Independence Day",
    (10, 2):  "Gandhi Jayanti",
    (11, 1):  "Andhra Pradesh Statehood Day",
    (12, 25): "Christmas",
    (1, 1):   "New Year",
    (5, 1):   "Labour Day",
    (4, 14):  "Ambedkar Jayanti",
    (10, 24): "Diwali",
}


def build_date_dim(start: date = date(2019,1,1), end: date = date(2026,1,1)) -> pd.DataFrame:
    dates = pd.date_range(start, end, freq="D")
    df = pd.DataFrame({"full_date": dates})
    df["date_key"]    = df["full_date"].dt.strftime("%Y%m%d").astype(int)
    df["year"]        = df["full_date"].dt.year
    df["quarter"]     = df["full_date"].dt.quarter
    df["month"]       = df["full_date"].dt.month
    df["month_name"]  = df["full_date"].dt.strftime("%B")
    df["week_of_year"]= df["full_date"].dt.isocalendar().week.astype(int)
    df["day_of_month"]= df["full_date"].dt.day
    df["day_of_week"] = df["full_date"].dt.dayofweek
    df["day_name"]    = df["full_date"].dt.strftime("%A")
    df["is_weekend"]  = (df["day_of_week"] >= 5).astype(int)
    df["is_holiday"]  = df["full_date"].dt.date.apply(lambda d: int(d in HOLIDAYS))
    df["holiday_name"]= df["full_date"].apply(
        lambda d: HOLIDAY_NAMES.get((d.month, d.day), None)
    )
    df["full_date"] = df["full_date"].dt.date
    return df


def load_dim_date(engine):
    df = build_date_dim()
    df.to_sql("dim_date", con=engine, if_exists="append", index=False, method="multi",
              chunksize=500)
    logger.info("dim_date loaded: %d rows", len(df))


# --- DIM_ROUTE ----------------------------------------------------------------

def load_dim_route(engine, apsrtc_df: pd.DataFrame, flights_df: pd.DataFrame, rail_df: pd.DataFrame = None):
    routes = set()

    if apsrtc_df is not None and "route" in apsrtc_df.columns:
        routes.update(apsrtc_df["route"].dropna().unique().tolist())

    if flights_df is not None:
        for _, row in flights_df.iterrows():
            src = str(row.get("source", "")).strip()
            dst = str(row.get("destination", "")).strip()
            if src and dst:
                routes.add(f"{src}-{dst}")

    if rail_df is not None:
        for _, row in rail_df.iterrows():
            src = str(row.get("source_station", "")).strip()
            dst = str(row.get("destination_station", "")).strip()
            if src and dst:
                routes.add(f"{src}-{dst}")

    route_rows = []
    for r in sorted(routes):
        parts = str(r).split("-", 1)
        src  = parts[0].strip() if len(parts) > 0 else None
        dst  = parts[1].strip() if len(parts) > 1 else None
        route_rows.append({"route_name": r, "source_city": src, "destination_city": dst})

    df = pd.DataFrame(route_rows)
    df.to_sql("dim_route", con=engine, if_exists="append", index=False, method="multi",
              chunksize=200)
    logger.info("dim_route loaded: %d rows", len(df))


# --- DIM_TRANSPORT_MODE -------------------------------------------------------

def load_dim_transport_mode(engine, apsrtc_df: pd.DataFrame, flights_df: pd.DataFrame):
    rows = []

    # APSRTC bus types
    if apsrtc_df is not None and "bus_type" in apsrtc_df.columns:
        for bt in apsrtc_df["bus_type"].dropna().unique():
            rows.append({"mode_name": "Bus", "sub_type": str(bt), "operator": "APSRTC"})

    # Flights -- by airline
    if flights_df is not None and "airline" in flights_df.columns:
        for airline in flights_df["airline"].dropna().unique():
            rows.append({"mode_name": "Flight", "sub_type": "Economy", "operator": str(airline)})

    # Railways
    rows.append({"mode_name": "Railway", "sub_type": "Train", "operator": "Indian Railways"})

    df = pd.DataFrame(rows).drop_duplicates()
    df.to_sql("dim_transport_mode", con=engine, if_exists="append", index=False,
              method="multi", chunksize=200)
    logger.info("dim_transport_mode loaded: %d rows", len(df))


# --- DIM_LOCATION -------------------------------------------------------------

def load_dim_location(engine, apsrtc_df: pd.DataFrame, flights_df: pd.DataFrame,
                       rail_df: pd.DataFrame):
    rows = []

    if apsrtc_df is not None and "depot" in apsrtc_df.columns:
        for depot in apsrtc_df["depot"].dropna().unique():
            rows.append({"location_name": str(depot), "location_type": "Depot",
                         "city": str(depot), "state": "Andhra Pradesh"})

    if flights_df is not None:
        for col in ["source", "destination"]:
            if col in flights_df.columns:
                for loc in flights_df[col].dropna().unique():
                    rows.append({"location_name": str(loc), "location_type": "Airport",
                                 "city": str(loc), "state": None})

    if rail_df is not None:
        for col in ["source_station", "destination_station"]:
            if col in rail_df.columns:
                for st in rail_df[col].dropna().unique():
                    rows.append({"location_name": str(st), "location_type": "Station",
                                 "city": str(st), "state": None})

    df = pd.DataFrame(rows).drop_duplicates(subset=["location_name", "location_type"])
    df.to_sql("dim_location", con=engine, if_exists="append", index=False, method="multi",
              chunksize=200)
    logger.info("dim_location loaded: %d rows", len(df))


# --- FACT_TRANSPORT -----------------------------------------------------------

def _get_route_keys(engine):
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT route_key, route_name FROM dim_route")).fetchall()
    return {r[1]: r[0] for r in rows}


def _get_mode_keys(engine):
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT mode_key, mode_name, sub_type, operator FROM dim_transport_mode")).fetchall()
    return {(r[1], r[2], r[3]): r[0] for r in rows}


def _get_location_keys(engine):
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT location_key, location_name, location_type FROM dim_location")).fetchall()
    return {(r[1], r[2]): r[0] for r in rows}


def _date_key(d) -> int:
    try:
        return int(pd.to_datetime(d).strftime("%Y%m%d"))
    except Exception:
        return 20240101


def load_fact_apsrtc(engine, df: pd.DataFrame):
    route_keys = _get_route_keys(engine)
    mode_keys  = _get_mode_keys(engine)
    loc_keys   = _get_location_keys(engine)

    def_rk = next(iter(route_keys.values())) if route_keys else 1
    def_mk = next(iter(mode_keys.values())) if mode_keys else 1
    def_lk = next(iter(loc_keys.values())) if loc_keys else 1

    records = []
    for _, row in df.iterrows():
        rk = route_keys.get(str(row.get("route", "")), def_rk)
        mk = mode_keys.get(("Bus", str(row.get("bus_type", "")), "APSRTC"), def_mk)
        lk = loc_keys.get((str(row.get("depot", "")), "Depot"), def_lk)

        records.append({
            "date_key":          _date_key(row.get("date")),
            "route_key":         rk,
            "mode_key":          mk,
            "location_key":      lk,
            "passenger_count":   int(row.get("passengers", 0)),
            "capacity":          int(row.get("capacity", 0)),
            "occupancy_rate":    float(row.get("occupancy_rate", 0)),
            "distance_km":       float(row.get("distance_km", 0)),
            "revenue":           float(row.get("revenue", 0)),
            "fare_per_passenger":float(row.get("fare_per_passenger", 0)),
            "fuel_liters":       float(row.get("fuel_consumed_liters", 0)),
            "seats_remaining":   int(row.get("capacity", 0)) - int(row.get("passengers", 0)),
            "source_dataset":    "apsrtc",
        })

    fact_df = pd.DataFrame(records)
    fact_df.to_sql("fact_transport", con=engine, if_exists="append", index=False,
                   method="multi", chunksize=200)
    logger.info("fact_transport (APSRTC): %d rows loaded", len(fact_df))


def load_fact_flights(engine, df: pd.DataFrame):
    route_keys = _get_route_keys(engine)
    mode_keys  = _get_mode_keys(engine)
    loc_keys   = _get_location_keys(engine)

    def_rk = next(iter(route_keys.values())) if route_keys else 1
    def_mk = next(iter(mode_keys.values())) if mode_keys else 1
    def_lk = next(iter(loc_keys.values())) if loc_keys else 1

    records = []
    for _, row in df.iterrows():
        src_dst = f"{row.get('source','')}-{row.get('destination','')}"
        rk = route_keys.get(src_dst, def_rk)
        airline = str(row.get("airline", "Unknown"))
        mk = mode_keys.get(("Flight", "Economy", airline), def_mk)
        src = str(row.get("source", ""))
        lk = loc_keys.get((src, "Airport"), def_lk)

        records.append({
            "date_key":          _date_key(row.get("date_of_journey")),
            "route_key":         rk,
            "mode_key":          mk,
            "location_key":      lk,
            "price":             float(row.get("price", 0)),
            "duration_minutes":  int(row.get("duration_minutes", 0)) if not pd.isna(row.get("duration_minutes", np.nan)) else None,
            "num_stops":         int(row.get("num_stops", 0)),
            "source_dataset":    "flights",
        })

    fact_df = pd.DataFrame(records)
    fact_df.to_sql("fact_transport", con=engine, if_exists="append", index=False,
                   method="multi", chunksize=200)
    logger.info("fact_transport (Flights): %d rows loaded", len(fact_df))


def load_fact_railways(engine, df: pd.DataFrame):
    route_keys = _get_route_keys(engine)
    loc_keys   = _get_location_keys(engine)

    def_rk = next(iter(route_keys.values())) if route_keys else 1
    def_lk = next(iter(loc_keys.values())) if loc_keys else 1

    with engine.connect() as conn:
        mk_row = conn.execute(text("SELECT mode_key FROM dim_transport_mode WHERE mode_name='Railway' LIMIT 1")).fetchone()
    mk = mk_row[0] if mk_row else 1

    records = []
    for _, row in df.iterrows():
        src = str(row.get("source_station",""))
        dst = str(row.get("destination_station",""))
        route_name = f"{src}-{dst}"
        rk = route_keys.get(route_name, def_rk)
        lk = loc_keys.get((src, "Station"), def_lk)

        records.append({
            "date_key":           20240101,   # schedule data -- no specific date
            "route_key":          rk,
            "mode_key":           mk,
            "location_key":       lk,
            "train_distance_km":  float(row.get("distance", 0)),
            "num_classes":        int(row.get("num_classes", 0)),
            "duration_minutes":   int(row.get("duration_minutes", 0)) if not pd.isna(row.get("duration_minutes", np.nan)) else None,
            "source_dataset":     "railways",
        })

    fact_df = pd.DataFrame(records)
    fact_df.to_sql("fact_transport", con=engine, if_exists="append", index=False,
                   method="multi", chunksize=200)
    logger.info("fact_transport (Railways): %d rows loaded", len(fact_df))


# --- Main load runner ----------------------------------------------------------

def run():
    logger.info("=== Warehouse Load START ===")
    engine = get_engine()

    # Create schema
    create_schema(engine)

    # Load processed files
    apsrtc_path  = DATA_PROCESSED_DIR / "apsrtc_clean.csv"
    flights_path = DATA_PROCESSED_DIR / "flights_clean.csv"
    rail_path    = DATA_PROCESSED_DIR / "railways_clean.csv"

    apsrtc_df  = pd.read_csv(apsrtc_path)  if apsrtc_path.exists()  else None
    flights_df = pd.read_csv(flights_path) if flights_path.exists() else None
    rail_df    = pd.read_csv(rail_path)    if rail_path.exists()    else None

    # -- Clear existing data (for re-runs) -------------------------------------
    with engine.connect() as conn:
        for t in ["fact_predictions", "fact_transport", "dim_route", "dim_transport_mode", "dim_location", "dim_date"]:
            try:
                conn.execute(text(f"DELETE FROM {t}"))
                conn.commit()
            except Exception:
                pass
    logger.info("Existing dimension/fact data cleared.")

    # Load dims
    logger.info("[1/5] Loading dim_date...")
    load_dim_date(engine)

    logger.info("[2/5] Loading dim_route...")
    load_dim_route(engine, apsrtc_df, flights_df, rail_df)

    logger.info("[3/5] Loading dim_transport_mode...")
    load_dim_transport_mode(engine, apsrtc_df, flights_df)

    logger.info("[4/5] Loading dim_location...")
    load_dim_location(engine, apsrtc_df, flights_df, rail_df)

    # Load facts
    logger.info("[5/5] Loading fact_transport...")
    if apsrtc_df is not None:
        load_fact_apsrtc(engine, apsrtc_df)
    if flights_df is not None:
        load_fact_flights(engine, flights_df)
    if rail_df is not None:
        load_fact_railways(engine, rail_df)

    # Load predictions if available
    pred_path = Path(__file__).resolve().parent.parent.parent / "outputs" / "predictions" / "demand_predictions.csv"
    if pred_path.exists():
        try:
            from src.ml.predict import load_predictions_to_db
            pred_df = pd.read_csv(pred_path)
            load_predictions_to_db(pred_df)
            logger.info("Synchronized fact_predictions table with current dimension keys.")
        except Exception as e:
            logger.warning("Could not sync predictions to DB: %s", e)

    logger.info("=== Warehouse Load END ===")


if __name__ == "__main__":
    run()
