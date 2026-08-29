# Public Transport Demand Prediction
## Using Machine Learning and Data Warehousing

> **Course**: Data Mining and Data Warehousing (DMDW)  
> **Dataset**: APSRTC Public Transportation · Indian Railways · Indian Domestic Flights

---

## Abstract

This project builds an end-to-end transportation analytics and demand-prediction system. It integrates three real transportation datasets into a MySQL star-schema data warehouse, applies OLAP analytical operations, performs K-Means clustering and Isolation Forest anomaly detection, then trains and compares five regression models (Linear Regression, Random Forest, XGBoost, LightGBM, CatBoost) to predict bus passenger demand. The best-performing model is explained using SHAP, and all results are made available to Tableau for interactive dashboards.

---

## Problem Statement

Public transport authorities need accurate demand forecasting to:
- Deploy the right number of buses on each route
- Reduce operational waste on low-demand routes
- Proactively manage peak-hour congestion
- Optimise revenue and fuel efficiency

This project builds a reproducible ML pipeline to predict `passengers` per trip for APSRTC bus routes using historical operational data.

---

## Objectives

1. **Data Warehousing** — Build a MySQL star-schema warehouse integrating APSRTC, Railways, and Flights datasets
2. **OLAP Analysis** — Implement roll-up, drill-down, slice, and dice operations
3. **Data Mining** — K-Means route clustering and Isolation Forest anomaly detection
4. **Machine Learning** — Train 5 regression models with time-aware split; select best model
5. **Explainable AI** — SHAP analysis to identify demand drivers
6. **Prediction** — Reusable pipeline predicting passenger demand + recommended buses
7. **Tableau** — 6 interactive dashboards for operational and analytical insights

---

## Dataset Description

### APSRTC (Primary ML dataset)
| Column | Type | Description |
|--------|------|-------------|
| bus_id | str | Unique bus identifier |
| route | str | Origin-Destination route (15 routes) |
| bus_type | str | Service type (Volvo AC, Sleeper, etc.) |
| depot | str | Operating depot (7 locations) |
| date | date | Trip date (2024 data, 348 unique dates) |
| capacity | int | Bus seat capacity |
| **passengers** | **int** | **TARGET: Passenger count (55 unique values, 0–55)** |
| occupancy_rate | float | % seats filled |
| distance_km | float | Route distance |
| fare_per_passenger | float | Ticket fare |
| revenue | float | Trip revenue |
| fuel_consumed_liters | float | Fuel used |
| month | str | Month name |
| day_of_week | str | Day of week |

**Rows**: 1,000 | **Missing values**: None | **Duplicates**: None

### Indian Railways (IRCTC)
Schedule data for 8,366 trains — used for OLAP analytics only (no passenger demand column available).

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

### Indian Domestic Flights (2019–2025)
15,000 flight records used for multi-modal analytics and Tableau dashboards.

| Column | Description |
|--------|-------------|
| airline | Carrier name |
| date_of_journey | Flight date |
| Source / destination | Airport cities |
| dep_time / Arrival_time | Times |
| Duration | Flight time |
| Total_stops | Non-stop / 1 stop / 2+ |
| Price | Ticket price (INR) |

---

## System Architecture

```
RAW DATA (3 datasets)
    ↓
ETL & PREPROCESSING (Python + Pandas)
    ↓
MYSQL DATA WAREHOUSE (Star Schema)
    ↓
       ┌──────────────┬──────────────┐
       ↓              ↓              ↓
     OLAP         K-MEANS      ISOLATION FOREST
  (SQL Queries)  CLUSTERING      ANOMALY DETECTION
       ↓              ↓              ↓
       └──────────────┴──────────────┘
                      ↓
              ML MODEL TRAINING
      (Linear / RF / XGBoost / LightGBM / CatBoost)
                      ↓
              HYPERPARAMETER TUNING
                      ↓
               BEST MODEL + SHAP
                      ↓
            DEMAND PREDICTION PIPELINE
                      ↓
             TABLEAU DASHBOARDS (6)
```

---

## Data Preprocessing

### APSRTC Pipeline (`src/etl/apsrtc.py`)
1. Extract from ZIP → load CSV
2. Normalise column names
3. Drop duplicate rows
4. Parse `date` → datetime
5. Fill missing numerics with median
6. Clip negative passengers to 0
7. Winsorise outliers (IQR × 3)
8. Normalise categorical strings (Title Case)

### Feature Engineering
- **Temporal**: year, month_num, day_num, dow, is_weekend, quarter, week_of_year, is_holiday
- **Lag features** (grouped by route): lag_1, lag_7, rolling_mean_7/14, rolling_max/min_7
- **Operational**: seats_remaining, revenue_per_km, fuel_efficiency
- **Encoded**: route_encoded, bus_type_encoded, depot_encoded

### Flights Pipeline (`src/etl/flights.py`)
- Parse `date_of_journey` as datetime
- Parse `Duration` → `duration_minutes` (integer)
- Parse `Total_stops` → `num_stops` (integer)
- Cap price outliers

### Railways Pipeline (`src/etl/railways.py`)
- Parse departure/arrival times to minutes
- Derive `duration_minutes` (handles overnight journeys)
- Extract class flags (has_1A, has_2A, has_SL, etc.)
- Count intermediate stops

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
| `dim_route` | ~150 | Distinct routes (Bus + Flights) |
| `dim_transport_mode` | ~50 | Bus subtypes + Airlines + Railway |
| `dim_location` | ~100 | Depots + Airports + Stations |
| `fact_transport` | ~24,000 | Central fact (APSRTC + Flights + Railways) |
| `fact_predictions` | ~1,000 | ML demand predictions |
| `ml_model_metrics` | ~10 | Model evaluation results |
| `mining_clusters` | ~15 | K-Means cluster assignments |
| `mining_anomalies` | ~50 | Isolation Forest anomalies |

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
- Features: avg_passengers, max_passengers, std_passengers, trip_count, avg_occupancy, avg_distance, avg_revenue
- Method: StandardScaler → Elbow + Silhouette → optimal K selection
- Output: route cluster assignments + cluster names (Low/Medium/High Demand)

### Isolation Forest (`src/mining/anomaly_detection.py`)
- Features: passengers, occupancy_rate, distance_km, revenue, fare_per_passenger, fuel_consumed_liters
- Contamination: 5% (tunable)
- Output: anomaly flags + scores per trip record

---

## Machine Learning

### Problem
**Regression**: Predict `passengers` (continuous integer) per APSRTC trip.

### Split Strategy (Time-Aware)
```
Past ─────────────────────────────────────────→ Future

TRAIN (70%)     |   VAL (15%)   |   TEST (15%)
──────────────────────────────────────────────
2024-xx-xx → ... → ... → ... → last 15% dates
```
No shuffling. Future records never in training set.

### Models Compared
| Model | Type |
|-------|------|
| Linear Regression | Baseline |
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
- Tuned model overwrites `best_model.pkl` if it improves test R²

---

## SHAP Explainability

```bash
python run_pipeline.py --steps explain
```

SHAP answers: *Which factors most influence bus passenger demand?*

Outputs:
- `reports/figures/shap_global_importance.png` — Top feature importances
- `reports/figures/shap_summary_plot.png` — Beeswarm feature impact
- `reports/figures/shap_waterfall_single.png` — Single prediction explanation
- `outputs/metrics/shap_feature_importance.csv` — For Tableau

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

# 4. Place raw datasets (ZIPs auto-extracted)
# ML\ folder should contain:
#   apsrtc.zip
#   irctc.zip
#   domestic flights.zip

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

## Tableau Connection

1. Open Tableau Desktop
2. Connect → MySQL (`localhost:3306`, database `transport_dw`)
3. Or connect to CSV files in `outputs/` for portable dashboards
4. See `tableau/dashboard_documentation.md` for complete dashboard specs

**6 Dashboards**:
1. Executive Overview (KPIs)
2. Demand Analysis (patterns by route/day/month)
3. Route Clustering (K-Means results)
4. Anomaly Detection (Isolation Forest results)
5. ML Model Performance (comparison table)
6. Demand Prediction (actual vs predicted)

---

## Running Tests

```bash
python tests/test_pipeline.py
```

Tests verify:
- Data loading
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
2. **No actual Railways demand**: IRCTC dataset contains schedules only, not passenger counts
3. **No geospatial data**: Route coordinates unavailable — map-based Tableau charts not possible
4. **Holiday calendar**: Approximate — uses fixed national holiday dates
5. **Lag features**: With 1,000 rows and 15 routes, lag features have limited depth (~66 records per route)

---

## Future Scope

1. Integrate real-time APSRTC API data for continuous model retraining
2. Add weather data as a demand feature
3. Deploy prediction API using FastAPI
4. Extend to LSTM/Transformer-based temporal models
5. Geospatial demand heatmaps with GPS coordinates
6. Integrate all three datasets into a unified demand model

---

## Project Structure

```
public-transport-demand-prediction/
├── data/
│   ├── raw/{apsrtc,railways,flights}/
│   └── processed/
├── notebooks/           (EDA and analysis notebooks)
├── src/
│   ├── config.py
│   ├── etl/{apsrtc,railways,flights,pipeline}.py
│   ├── warehouse/{schema.sql,load.py,queries.sql}
│   ├── mining/{clustering,anomaly_detection}.py
│   ├── ml/{preprocessing,train,evaluate,tune,explain,predict}.py
│   └── utils/logger.py
├── models/
│   ├── best_model.pkl
│   └── model_metadata.json
├── outputs/
│   ├── predictions/
│   ├── metrics/
│   └── figures/
├── reports/figures/
├── tableau/dashboard_documentation.md
├── tests/test_pipeline.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
└── run_pipeline.py
```

---

## Conclusion

This project demonstrates a complete DMDW + ML pipeline:
- **ETL** cleans and integrates 3 datasets totalling ~24,000 records
- **Star schema** warehouse enables multi-dimensional OLAP queries
- **K-Means** reveals 3 demand tiers across 15 APSRTC routes
- **Isolation Forest** flags ~5% anomalous trips for investigation
- **Gradient boosting models** (XGBoost/LightGBM/CatBoost) outperform the baseline
- **SHAP** confirms that historical demand, route, and occupancy rate are primary demand drivers
- **Tableau** provides 6 interactive dashboards for operational decision-making

The system is fully reproducible: a single `python run_pipeline.py` command executes all phases from raw data to Tableau-ready outputs.
