# Public Transport Demand Prediction
## Using Machine Learning and Data Warehousing

> **Course**: Data Mining and Data Warehousing (DMDW)  
> **Dataset**: APSRTC Public Transportation · Indian Railways · Indian Domestic Flights

---

## Abstract

This project builds an end-to-end transportation analytics and demand-prediction system. It integrates three real transportation datasets into a MySQL star-schema data warehouse, applies OLAP analytical operations, performs K-Means clustering and Isolation Forest anomaly detection across all three transport modes, then trains and compares five regression models (Ridge, Random Forest, XGBoost, LightGBM, CatBoost) to predict passenger demand. The best-performing model is explained using SHAP.

---

## Problem Statement

Public transport authorities need accurate demand forecasting to:
- Deploy the right number of vehicles on each route
- Reduce operational waste on low-demand routes
- Proactively manage peak-hour congestion
- Optimise revenue and fuel efficiency

This project builds a reproducible ML pipeline to predict `passengers` per trip across Bus, Rail, and Air transport using historical operational data.

---

## Objectives

1. **Data Warehousing** — Build a MySQL star-schema warehouse integrating APSRTC, Railways, and Flights datasets
2. **OLAP Analysis** — Implement roll-up, drill-down, slice, and dice operations
3. **Data Mining** — K-Means route clustering and Isolation Forest anomaly detection across all 3 modes
4. **Machine Learning** — Train 5 regression models on combined ~24,366 rows with time-aware split
5. **Explainable AI** — SHAP analysis to identify demand drivers
6. **Prediction** — Reusable pipeline predicting passenger demand + recommended vehicles

---

## Dataset Description

Raw datasets are stored in the `datasets/` folder at the project root.

### APSRTC — `datasets/apstrc.csv` (ML dataset — Bus)
| Column | Type | Description |
|--------|------|-------------|
| bus_id | str | Unique bus identifier |
| route | str | Origin-Destination route (15 routes) |
| bus_type | str | Service type (Volvo AC, Sleeper, Semi-Sleeper, Super Luxury, Express, Ordinary) |
| depot | str | Operating depot (7 locations) |
| date | date | Trip date (2024-01-01 → 2024-12-30) |
| capacity | int | Bus seat capacity |
| **passengers** | **int** | **TARGET: Passenger count (55 unique values)** |
| occupancy_rate | float | % seats filled |
| distance_km | float | Route distance |
| fare_per_passenger | float | Ticket fare |
| revenue | float | Trip revenue |
| fuel_consumed_liters | float | Fuel used |
| month | str | Month name |
| day_of_week | str | Day of week |

**Rows**: 1,000 | **Missing values**: None | **Duplicates**: None  
**Routes**: Kurnool-Hyderabad, Guntur-Hyderabad, Hyderabad-Vijayawada, Eluru-Hyderabad, Anantapur-Bangalore, Nellore-Chennai, Vijayawada-Visakhapatnam, Hyderabad-Tirupati, Hyderabad-Visakhapatnam, Kadapa-Hyderabad, Ongole-Hyderabad, Rajahmundry-Hyderabad, Vijayawada-Tirupati, Kakinada-Vijayawada, Chittoor-Bangalore  
**Depots**: Hyderabad, Guntur, Nellore, Kurnool, Visakhapatnam, Tirupati, Vijayawada

### Indian Railways (IRCTC) — `datasets/Irctc.csv` (ML dataset — Rail)
8,366 train records used for OLAP analytics and ML demand prediction.

| Column | Description |
|--------|-------------|
| train_no | Train number |
| train_name | Train name |
| source_station / destination_station | Start and end stations |
| departure_time / arrival_time | Timetable |
| distance | Route distance (km) |
| days_of_week | Operating days |
| classes | Coach classes available |
| intermediate_stops | All station stops |
| **passengers** | **Seeded: demand based on train type + distance (min=42, max=760, avg=216)** |

**Rows**: 8,366 | **Missing values**: None | **Duplicates**: None  
**Seeding logic**: Rajdhani (300–600) → Shatabdi (200–500) → Express (100–400) → Local/MEMU (50–250), scaled by route distance

### Indian Domestic Flights — `datasets/flights.csv` (ML dataset — Air)
15,000 flight records used for multi-modal analytics and ML demand prediction.

| Column | Description |
|--------|-------------|
| airline | Carrier name |
| date_of_journey | Flight date (2019–2025) |
| Source / destination | Airport cities |
| dep_time / Arrival_time | Times |
| Duration | Flight time |
| Total_stops | Non-stop / 1 stop / 2+ |
| Price | Ticket price (INR) |
| **passengers** | **Seeded: demand based on airline capacity tier + stops load factor + price (min=11, max=291, avg=83)** |

**Rows**: 15,000 | **Missing values**: None | **Duplicates**: None  
**Seeding logic**: Airline fleet capacity tier (IndiGo/SpiceJet=160, regional=72) × load factor by stops (non-stop: 75–98%, 3 stops: 30–60%) × price adjustment

---

## System Architecture

```
RAW DATA (3 datasets in datasets/)
    ↓
ETL & PREPROCESSING (Python + Pandas)
    ↓
MYSQL DATA WAREHOUSE (Star Schema)
    ↓
       ┌──────────────┬──────────────┐
       ↓              ↓              ↓
     OLAP         K-MEANS      ISOLATION FOREST
  (SQL Queries)  CLUSTERING      ANOMALY DETECTION
  (all 3 modes)  (all 3 modes)   (all 3 modes)
       ↓              ↓              ↓
       └──────────────┴──────────────┘
                      ↓
              ML MODEL TRAINING
      (Ridge / RF / XGBoost / LightGBM / CatBoost)
      (~24,366 rows: Bus + Rail + Air combined)
                      ↓
              HYPERPARAMETER TUNING
                      ↓
               BEST MODEL + SHAP
                      ↓
            DEMAND PREDICTION PIPELINE
                      ↓
              OUTPUT CSVs + CHARTS
```

---

## Data Preprocessing

### APSRTC Pipeline (`src/etl/apsrtc.py`)
Reads from: `data/raw/apsrtc/APSRTC_Transport_Data.csv`

1. Normalise column names
2. Drop duplicate rows
3. Parse `date` → datetime
4. Fill missing numerics with median
5. Clip negative passengers to 0
6. Winsorise outliers (IQR × 3)
7. Normalise categorical strings (Title Case)

### Feature Engineering
- **Temporal**: year, month_num, day_num, dow, is_weekend, quarter, week_of_year, is_holiday
- **Lag features** (grouped by route): lag_1, lag_7, rolling_mean_7/14, rolling_max/min_7
- **Historical means**: route_hist_mean, bustype_hist_mean, route_month_mean, route_bustype_mean
- **Encoded**: route_encoded, bus_type_encoded, depot_encoded

### Flights Pipeline (`src/etl/flights.py`)
Reads from: `data/raw/flights/flights.csv`

- Parse `date_of_journey` as datetime
- Parse `Duration` → `duration_minutes` (integer)
- Parse `Total_stops` → `num_stops` (integer)
- Cap price outliers (IQR × 3)

### Railways Pipeline (`src/etl/railways.py`)
Reads from: `data/raw/railways/IRCTC_cleaned.csv`

- Parse departure/arrival times to minutes
- Derive `duration_minutes` (handles overnight journeys)
- Extract class flags (has_1A, has_2A, has_SL, etc.)
- Count intermediate stops

---

## Dataset Setup

The ETL pipeline reads from `data/raw/`. Copy the datasets from `datasets/` into the expected locations before running the pipeline:

```
datasets/apstrc.csv  →  data/raw/apsrtc/APSRTC_Transport_Data.csv
datasets/Irctc.csv   →  data/raw/railways/IRCTC_cleaned.csv
datasets/flights.csv →  data/raw/flights/flights.csv
```

```bash
# Windows (PowerShell)
New-Item -ItemType Directory -Force -Path data/raw/apsrtc, data/raw/railways, data/raw/flights
Copy-Item datasets/apstrc.csv  data/raw/apsrtc/APSRTC_Transport_Data.csv
Copy-Item datasets/Irctc.csv   data/raw/railways/IRCTC_cleaned.csv
Copy-Item datasets/flights.csv data/raw/flights/flights.csv
```

```bash
# Linux / macOS
mkdir -p data/raw/apsrtc data/raw/railways data/raw/flights
cp datasets/apstrc.csv  data/raw/apsrtc/APSRTC_Transport_Data.csv
cp datasets/Irctc.csv   data/raw/railways/IRCTC_cleaned.csv
cp datasets/flights.csv data/raw/flights/flights.csv
```

---

## ETL Pipeline

```bash
# Run all preprocessing
python run_pipeline.py --steps etl

# Load into MySQL
python run_pipeline.py --steps load_dw
```

Processed files saved to `data/processed/`:
- `apsrtc_clean.csv` — cleaned APSRTC
- `apsrtc_features.csv` — feature-engineered for ML
- `railways_clean.csv` — cleaned railways
- `flights_clean.csv` — cleaned flights

---

## Data Warehouse Design

**Database**: `transport_dw` (MySQL)

### Star Schema

```
                    dim_date
                       │
dim_route ──────→ fact_transport ←── dim_transport_mode
                       │
                  dim_location
```

### Tables
| Table | Rows (approx) | Description |
|-------|--------------|-------------|
| `dim_date` | 2,557 | Calendar dates 2019–2026 |
| `dim_route` | ~150 | Distinct routes (Bus + Flights + Rail) |
| `dim_transport_mode` | ~50 | Bus subtypes + Airlines + Railway |
| `dim_location` | ~100 | Depots + Airports + Stations |
| `fact_transport` | ~24,366 | Central fact (APSRTC + Flights + Railways) |
| `fact_predictions` | ~24,366 | ML demand predictions |
| `ml_model_metrics` | ~10 | Model evaluation results |
| `mining_clusters` | ~150 | K-Means cluster assignments |
| `mining_anomalies` | ~1,200 | Isolation Forest anomalies |

---

## OLAP Operations

Implemented in `src/warehouse/queries.sql`:

| Operation | Example |
|-----------|---------|
| **Roll-up** | Daily → Monthly → Quarterly → Yearly passenger totals |
| **Drill-down** | Year 2024 → November → Day 1 → Route level |
| **Slice** | Filter Transport Mode = Bus only |
| **Dice** | Bus + August + Weekdays + specific routes |

---

## Data Mining

### K-Means Clustering (`src/mining/clustering.py`)
- **Datasets**: APSRTC (Bus) + IRCTC (Rail) + Flights (Air) — all routes clustered together
- Features: avg_passengers, max_passengers, std_passengers, trip_count, avg_occupancy, avg_distance_km, avg_fare
- Method: StandardScaler → Elbow + Silhouette → optimal K selection
- Output: `outputs/predictions/route_clusters.csv`

### Isolation Forest (`src/mining/anomaly_detection.py`)
- **Datasets**: APSRTC (Bus) + IRCTC (Rail) + Flights (Air) — anomalies detected across all modes
- Shared features: passengers, occupancy_rate, distance_km, fare_per_passenger
- Contamination: 5% per mode
- Output: `outputs/predictions/transport_anomalies.csv`

---

## Machine Learning

### Combined Training Data
| Dataset | Rows | Transport Mode |
|---------|------|---------------|
| APSRTC | 1,000 | Bus |
| IRCTC | 8,366 | Rail |
| Flights | 15,000 | Air |
| **Total** | **~24,366** | **Multi-modal** |

### Split Strategy (Time-Aware)
```
Past ─────────────────────────────────────────→ Future

TRAIN (70%)     |   VAL (15%)   |   TEST (15%)
──────────────────────────────────────────────
~17,056 rows        ~3,655 rows     ~3,655 rows
```
No shuffling. Future records never in training set.

### Models Compared
| Model | Type |
|-------|------|
| Ridge | Baseline |
| Random Forest | Traditional Ensemble |
| XGBoost | Gradient Boosting |
| LightGBM | Gradient Boosting |
| CatBoost | Gradient Boosting |

### Evaluation Metrics
- MAE (Mean Absolute Error)
- RMSE (Root Mean Squared Error)
- MAPE (Mean Absolute Percentage Error)
- R² (Coefficient of Determination)

Metrics saved to `outputs/metrics/model_metrics.csv`

---

## Hyperparameter Tuning

```bash
python run_pipeline.py --steps tune
```

- **Method**: RandomizedSearchCV with TimeSeriesSplit (5 folds)
- **Scoring**: Negative MAE
- **Models tuned**: XGBoost, LightGBM, CatBoost
- Tuned model overwrites `best_model.pkl` only if CV MAE improves

---

## SHAP Explainability

```bash
python run_pipeline.py --steps explain
```

SHAP answers: *Which factors most influence passenger demand?*

Outputs:
- `reports/figures/shap_global_importance.png` — Top feature importances
- `reports/figures/shap_summary_plot.png` — Beeswarm feature impact
- `reports/figures/shap_waterfall_single.png` — Single prediction explanation
- `outputs/metrics/shap_feature_importance.csv`

---

## Prediction Pipeline

```bash
python run_pipeline.py --steps predict
```

### Single prediction
```python
from src.ml.predict import predict_single
result = predict_single(
    route="Kurnool-Hyderabad",
    date="2024-12-15",
    bus_type="Volvo Ac",
    distance_km=326.0,
    capacity=49,
    is_holiday=0,
    bus_capacity=50,
)
# → {'predicted_demand': 38, 'demand_category': 'Medium', 'recommended_buses': 1}
```

Bus recommendation formula:
```
recommended_buses = ceil(predicted_demand / bus_capacity)
```

Bus capacity is **configurable** via `.env` (`BUS_CAPACITY=50`).

---

## Environment Setup

```bash
# 1. Clone / navigate to project
cd public-transport-demand-prediction

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your MySQL credentials

# 4. Copy datasets to expected locations (see Dataset Setup section above)

# 5. Run full pipeline
python run_pipeline.py
```

---

## Running Individual Steps

```bash
python run_pipeline.py --steps etl           # ETL only
python run_pipeline.py --steps load_dw       # Load MySQL warehouse
python run_pipeline.py --steps mine          # Clustering + Anomaly detection
python run_pipeline.py --steps train         # Train all models
python run_pipeline.py --steps tune          # Hyperparameter tuning
python run_pipeline.py --steps explain       # SHAP analysis
python run_pipeline.py --steps predict       # Generate predictions
python run_pipeline.py --steps etl,train     # Multiple steps
python run_pipeline.py                       # All steps
```

---

## Running Tests

```bash
python tests/test_pipeline.py
```

Tests verify:
- Data loading from all 3 datasets
- Preprocessing (no null targets, no negatives)
- Feature engineering columns present
- No data leakage in time-aware split
- Model loads and predicts numeric values
- Prediction pipeline returns valid output

---

## Results

> Run `python run_pipeline.py` to generate actual results.  
> Model metrics will be saved to `outputs/metrics/model_metrics.csv`.

---

## Limitations

1. **APSRTC dataset size**: 1,000 rows — sufficient for demonstration but small for production deep learning
2. **Seeded passenger counts**: IRCTC and Flights `passengers` columns are derived from heuristics, not real surveys
3. **IRCTC synthetic dates**: No actual trip dates in the schedule dataset — random dates assigned for time-aware split
4. **No geospatial data**: Route coordinates unavailable — map-based charts not possible
5. **Holiday calendar**: Approximate — uses 9 fixed Indian national holiday dates
6. **Lag features**: ~66 records per APSRTC route — limited lag depth

---

## Future Scope

1. Integrate real-time APSRTC API data for continuous model retraining
2. Add weather data as a demand feature
3. Deploy prediction API using FastAPI
4. Extend to LSTM/Transformer-based temporal models
5. Replace seeded passengers with real survey data for Rail and Air

---

## Project Structure

```
public-transport-demand-prediction/
├── datasets/
│   ├── apstrc.csv               ← APSRTC raw data (1,000 rows)
│   ├── Irctc.csv                ← Indian Railways (8,366 rows)
│   └── flights.csv              ← Domestic flights (15,000 rows)
├── data/
│   ├── raw/
│   │   ├── apsrtc/APSRTC_Transport_Data.csv
│   │   ├── railways/IRCTC_cleaned.csv
│   │   └── flights/flights.csv
│   └── processed/
├── notebooks/                   (EDA and analysis notebooks)
├── src/
│   ├── config.py
│   ├── etl/{apsrtc,railways,flights,pipeline}.py
│   ├── warehouse/{schema.sql,load.py,queries.sql}
│   ├── mining/{clustering,anomaly_detection}.py
│   ├── ml/{preprocessing,train,evaluate,tune,explain,predict}.py
│   └── utils/logger.py
├── models/
│   ├── best_model.pkl
│   ├── all_models.pkl
│   ├── tuned_model.pkl
│   └── model_metadata.json
├── outputs/
│   ├── predictions/
│   ├── metrics/
│   └── figures/
├── reports/figures/
├── tests/test_pipeline.py
├── requirements.txt
├── .env.example
├── .gitignore
├── PRD.md
├── Architecture.md
├── Workflow.md
└── README.md
```

---

## Conclusion

This project demonstrates a complete DMDW + ML pipeline:
- **ETL** cleans and integrates 3 datasets totalling ~24,366 records
- **Star schema** warehouse enables multi-dimensional OLAP queries
- **K-Means** reveals demand tiers across Bus, Rail, and Air routes
- **Isolation Forest** flags ~5% anomalous trips per transport mode
- **Gradient boosting models** (XGBoost/LightGBM/CatBoost) trained on all 3 transport modes
- **SHAP** identifies transport mode, capacity, and historical demand as primary demand drivers

The system is fully reproducible: a single `python run_pipeline.py` command executes all phases from raw data to final outputs.
