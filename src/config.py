"""
config.py — Central configuration for the Public Transport Demand Prediction project.
All paths, database settings, and ML hyperparameters are sourced from here.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ─── Load environment variables ───────────────────────────────────────────────
load_dotenv()

# ─── Project root ─────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).resolve().parent.parent

# ─── Data directories ─────────────────────────────────────────────────────────
DATA_RAW_DIR      = ROOT_DIR / os.getenv("DATA_RAW_DIR",       "data/raw")
DATA_PROCESSED_DIR = ROOT_DIR / os.getenv("DATA_PROCESSED_DIR", "data/processed")

RAW_APSRTC_DIR   = DATA_RAW_DIR / "apsrtc"
RAW_RAILWAYS_DIR = DATA_RAW_DIR / "railways"
RAW_FLIGHTS_DIR  = DATA_RAW_DIR / "flights"

# ─── Output directories ───────────────────────────────────────────────────────
MODELS_DIR       = ROOT_DIR / os.getenv("MODELS_DIR",   "models")
OUTPUTS_DIR      = ROOT_DIR / os.getenv("OUTPUTS_DIR",  "outputs")
FIGURES_DIR      = ROOT_DIR / "reports" / "figures"

PREDICTIONS_DIR  = OUTPUTS_DIR / "predictions"
METRICS_DIR      = OUTPUTS_DIR / "metrics"

# ─── Ensure directories exist ─────────────────────────────────────────────────
for _dir in [DATA_PROCESSED_DIR, MODELS_DIR, PREDICTIONS_DIR, METRICS_DIR, FIGURES_DIR]:
    _dir.mkdir(parents=True, exist_ok=True)

# ─── Database configuration ───────────────────────────────────────────────────
DB_HOST     = os.getenv("DB_HOST",     "localhost")
DB_PORT     = int(os.getenv("DB_PORT", "3306"))
DB_NAME     = os.getenv("DB_NAME",     "transport_dw")
DB_USER     = os.getenv("DB_USER",     "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# ─── ML configuration ─────────────────────────────────────────────────────────
RANDOM_SEED  = int(os.getenv("RANDOM_SEED", "42"))
TEST_SIZE    = float(os.getenv("TEST_SIZE",  "0.15"))
VAL_SIZE     = float(os.getenv("VAL_SIZE",   "0.15"))
BUS_CAPACITY = int(os.getenv("BUS_CAPACITY", "50"))

TARGET_COLUMN = "passengers"   # confirmed column name in APSRTC_Transport_Data.csv

# ─── Logging ──────────────────────────────────────────────────────────────────
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_LEVEL  = "INFO"
