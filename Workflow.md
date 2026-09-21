# Project Workflow

**Project**: Public Transport Demand Prediction  
**Entry Point**: `python run_pipeline.py`

---

## 1. Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your MySQL credentials (optional — pipeline works without MySQL)

# 3. Run the full pipeline
python run_pipeline.py
```

That single command runs all 7 steps in order and produces every output artifact.

---

## 2. Pipeline Steps Overview

```
Step 1: ETL          →  3 raw CSVs cleaned and feature-engineered
Step 2: Load DW      →  MySQL star-schema populated (optional)
Step 3: Mine         →  K-Means clusters + Isolation Forest anomalies
Step 4: Train        →  5 ML models trained, compared, best saved
Step 5: Tune         →  Best models hyperparameter-tuned
Step 6: Explain      →  SHAP charts + feature importance CSV
Step 7: Predict      →  Batch predictions + single demo
```

Each step is independent and can be run alone:

```bash
python run_pipeline.py --steps etl
python run_pipeline.py --steps mine
python run_pipeline.py --steps train
python run_pipeline.py --steps etl,train       # multiple steps
python run_pipeline.py --steps tune
python run_pipeline.py --steps explain
python run_pipeline.py --steps predict
python run_pipeline.py --steps load_dw
```

---

## 3. Step-by-Step Workflow

---

### Step 1 — ETL (`--steps etl`)

**Entry**: `src/etl/pipeline.py` → calls all 3 ETL modules

#### APSRTC (`src/etl/apsrtc.py`)

```
datasets/apstrc.csv
        │
        ├─ Normalise column names (lowercase, underscores)
        ├─ Drop duplicate rows
        ├─ Parse date → datetime
        ├─ Fill missing numerics with median
        ├─ Clip negative passengers to 0
        ├─ Winsorise passengers outliers (IQR × 3)
        ├─ Title-case string columns (route, bus_type, depot)
        │
        ├─ Feature Engineering:
        │   ├─ Temporal: year, month_num, day_num, dow, is_weekend,
        │   │            quarter, week_of_year, is_holiday
        │   ├─ Sort by [route, date] before computing any lag features
        │   ├─ Lag (per-route, shift(1)): lag_1, lag_7
        │   ├─ Rolling (per-route, shift(1)): rolling_mean_7/14,
        │   │           rolling_max/min_7, rolling_std_7
        │   ├─ Historical means (expanding, shift(1)):
        │   │   route_hist_mean, bustype_hist_mean,
        │   │   route_month_mean, route_bustype_mean
        │   └─ Encodings: route_encoded, bus_type_encoded, depot_encoded
        │
        ├─ Save: data/processed/apsrtc_clean.csv      (1,000 rows)
        └─ Save: data/processed/apsrtc_features.csv   (1,000 rows + 30+ features)
```

#### Railways (`src/etl/railways.py`)

```
datasets/Irctc.csv  (or data/raw/railways/IRCTC_cleaned.csv)
        │
        ├─ Normalise column names
        ├─ Drop duplicates
        ├─ Fill missing classes with 'GN'
        ├─ Process passengers column (numeric, clip ≥ 0)
        ├─ Parse departure_time / arrival_time → minutes
        ├─ Derive duration_minutes (handles overnight journeys)
        ├─ Expand classes → has_1A, has_2A, has_3A, has_SL, has_GN flags
        ├─ Count intermediate stops
        ├─ Classify train_type (Rajdhani/Shatabdi/Express/Local/etc.)
        ├─ Encode train_type_encoded
        ├─ Day flags: runs_weekday, runs_weekend, runs_daily
        │
        └─ Save: data/processed/railways_clean.csv    (8,366 rows)
```

#### Flights (`src/etl/flights.py`)

```
datasets/flights.csv  (or data/raw/flights/flights.csv)
        │
        ├─ Normalise column names, drop index column
        ├─ Drop duplicates
        ├─ Parse date_of_journey → datetime
        ├─ Parse dep_time / arrival_time → time objects
        ├─ Parse Duration → duration_minutes (e.g. '2h 30min' → 150)
        ├─ Parse Total_stops → num_stops (e.g. '1 stop' → 1)
        ├─ Temporal features: year, month, day, day_of_week, quarter, is_weekend
        ├─ Cap price outliers (IQR × 3)
        ├─ Process passengers column (numeric, clip ≥ 0)
        ├─ Encode airline_tier (1=full-service, 2=LCC, 3=regional)
        ├─ Encode airline_encoded, route_pair, route_encoded
        │
        └─ Save: data/processed/flights_clean.csv     (15,000 rows)
```

**Output verification:**

```
data/processed/
├── apsrtc_clean.csv       ← 1,000 rows, 14 cols, 0 nulls
├── apsrtc_features.csv    ← 1,000 rows, 40+ cols, 0 nulls in target
├── railways_clean.csv     ← 8,366 rows, 25+ cols
└── flights_clean.csv      ← 15,000 rows, 20+ cols
```

---

### Step 2 — Load Data Warehouse (`--steps load_dw`)

**Entry**: `src/warehouse/load.py`

> This step is **optional**. The pipeline continues if MySQL is unavailable.

```
data/processed/*.csv
        │
        ├─ Connect to MySQL (transport_dw)
        ├─ Populate dim_date (2019-01-01 → 2026-12-31, ~2,557 rows)
        ├─ Populate dim_route from all 3 datasets
        ├─ Populate dim_transport_mode (Bus subtypes, Airlines, Rail classes)
        ├─ Populate dim_location (Depots, Airports, Stations)
        ├─ Load fact_transport:
        │   ├─ APSRTC rows   (source_dataset = 'apsrtc')
        │   ├─ Railways rows (source_dataset = 'railways')
        │   └─ Flights rows  (source_dataset = 'flights')
        │
        └─ Total fact_transport: ~24,366 rows
```

**OLAP queries** available in `src/warehouse/queries.sql`:

| Operation | Query section | Example |
|---|---|---|
| Roll-up | Section 1 | Daily → Monthly → Quarterly → Yearly |
| Drill-down | Section 2 | Year 2024 → Nov → Day 1 → Route |
| Slice | Section 3 | mode_name = 'Bus' only |
| Dice | Section 4 | Bus + August + Weekdays + specific routes |
| KPIs | Section 5 | Total passengers, avg demand, revenue |
| Day-of-week | Section 6 | Demand pattern Mon–Sun |
| Holiday effect | Section 7 | Holiday vs normal day demand |
| Flight analytics | Section 8 | Price by route, stops, duration |

---

### Step 3 — Data Mining (`--steps mine`)

**Entry**: `src/mining/clustering.py` + `src/mining/anomaly_detection.py`

#### K-Means Clustering

```
apsrtc_clean.csv + railways_clean.csv + flights_clean.csv
        │
        ├─ Build route-level feature matrix per transport_mode:
        │   avg_passengers, max_passengers, min_passengers, std_passengers,
        │   trip_count, avg_occupancy, avg_distance_km, avg_fare
        │
        ├─ StandardScaler → X_scaled
        ├─ Elbow method (K=2..8): compute inertia per K
        ├─ Silhouette score per K
        ├─ Auto-select K = argmax(silhouette_scores)
        ├─ KMeans(n_clusters=K, n_init=20)
        ├─ Assign cluster names by avg_passengers rank:
        │   Lowest → 'Low Demand'
        │   Middle → 'Medium Demand' / 'Peak-Dependent'
        │   Highest → 'High Demand'
        │
        ├─ Save chart: outputs/figures/kmeans_elbow_silhouette.png
        ├─ Save chart: outputs/figures/kmeans_clusters.png
        └─ Save CSV:   outputs/predictions/route_clusters.csv
```

#### Isolation Forest Anomaly Detection

```
apsrtc_clean.csv + railways_clean.csv + flights_clean.csv
        │
        ├─ Unified features (shared across modes):
        │   passengers, occupancy_rate, distance_km, fare_per_passenger
        │
        ├─ StandardScaler → X_scaled
        ├─ IsolationForest(contamination=0.05, n_estimators=200)
        ├─ Score each record → anomaly_score (more negative = more anomalous)
        ├─ Label: is_anomaly = 1 if predict == -1
        │
        ├─ Log breakdown:
        │   Bus:  ~50 anomalies  (5% of 1,000)
        │   Rail: ~418 anomalies (5% of 8,366)
        │   Air:  ~750 anomalies (5% of 15,000)
        │
        ├─ Save chart: outputs/figures/anomaly_detection.png
        ├─ Save chart: outputs/figures/anomaly_by_mode.png
        └─ Save CSV:   outputs/predictions/transport_anomalies.csv
```

---

### Step 4 — ML Training (`--steps train`)

**Entry**: `src/ml/train.py` → calls `src/ml/preprocessing.py`

#### Data Preparation

```
apsrtc_features.csv + railways_clean.csv + flights_clean.csv
        │
        ├─ _load_apsrtc()   → transport_mode_encoded=0, 1,000 rows
        ├─ _load_railways() → transport_mode_encoded=1, 8,366 rows
        │   (synthetic dates assigned: 2019-2024, seed=42)
        ├─ _load_flights()  → transport_mode_encoded=2, 15,000 rows
        │
        ├─ pd.concat → ~24,366 rows unified DataFrame
        │
        ├─ Shared feature engineering (on combined data):
        │   ├─ Sort by [route, date]
        │   ├─ Lag features: lag_1, lag_7
        │   ├─ Rolling: rolling_mean_7/14, rolling_max/min/std_7
        │   ├─ Historical means: route_hist_mean, modetype_hist_mean,
        │   │                    route_month_mean, route_modetype_mean
        │   └─ Encodings: route_encoded, mode_type_encoded, operator_encoded
        │
        ├─ Sort by date only → time-aware split:
        │   TRAIN: first 70%  (~17,056 rows)
        │   VAL:   next  15%  (~3,655 rows)
        │   TEST:  last  15%  (~3,655 rows)
        │
        └─ NaN fill using TRAIN statistics only:
            lag/rolling → per-route median from TRAIN
            rolling_std → global std from TRAIN
```

#### Model Training

```
For each model (Ridge / RandomForest / XGBoost / LightGBM / CatBoost):
    │
    ├─ Fit on X_train, y_train
    │   (gradient boosters use X_val for early stopping)
    │
    ├─ Predict on X_val  → val_metrics  (MAE, RMSE, MAPE, R²)
    ├─ Predict on X_test → test_metrics (MAE, RMSE, MAPE, R²)
    └─ Save predictions scatter plot

Best model = lowest VAL MAE
        │
        ├─ Save: models/best_model.pkl
        ├─ Save: models/all_models.pkl
        ├─ Save: models/model_metadata.json
        └─ Save: outputs/metrics/model_metrics.csv
```

---

### Step 5 — Hyperparameter Tuning (`--steps tune`)

**Entry**: `src/ml/tune.py`

```
X_train + X_val combined (no test leakage)
        │
        ├─ For XGBoost / LightGBM / CatBoost / RandomForest:
        │   ├─ RandomizedSearchCV (n_iter=25)
        │   ├─ TimeSeriesSplit (n_splits=5)
        │   ├─ Scoring: neg_mean_absolute_error
        │   └─ Log best params + CV MAE
        │
        ├─ Best tuned model = lowest CV MAE
        ├─ Save: models/tuned_model.pkl
        ├─ Save: models/tuned_model_metadata.json
        │
        └─ Compare tuned CV MAE vs previous best val MAE:
            If improved → overwrite models/best_model.pkl
            Else        → keep existing best_model.pkl
```

---

### Step 6 — SHAP Explainability (`--steps explain`)

**Entry**: `src/ml/explain.py`

```
models/best_model.pkl + test set (sample n=200)
        │
        ├─ SHAP TreeExplainer (works for CatBoost/XGB/LGBM/RF)
        │   LinearExplainer fallback for Ridge
        │
        ├─ Compute shap_values [200 × 27]
        │
        ├─ Global importance bar chart:
        │   mean(|SHAP|) per feature → top 20
        │   Save: reports/figures/shap_global_importance.png
        │
        ├─ Beeswarm summary plot:
        │   Feature impact distribution across all samples
        │   Save: reports/figures/shap_summary_plot.png
        │
        ├─ Waterfall plot (single prediction, record #0):
        │   Shows each feature's contribution to that prediction
        │   Save: reports/figures/shap_waterfall_single.png
        │
        ├─ Save: outputs/metrics/shap_feature_importance.csv
        └─ Save: outputs/metrics/shap_values.csv
```

**Typical top SHAP features:**

```
1. capacity               — seat count is the strongest demand signal
2. rolling_mean_14        — 2-week historical demand per route
3. mode_type_encoded      — bus_type / train_type / airline matters
4. transport_mode_encoded — Bus vs Rail vs Air demand levels differ
5. week_of_year           — seasonal demand patterns
6. rolling_mean_7         — 1-week historical demand
7. lag_7                  — same day last week
8. fare_per_passenger     — price sensitivity
```

---

### Step 7 — Prediction Pipeline (`--steps predict`)

**Entry**: `src/ml/predict.py`

#### Batch Predictions

```
models/best_model.pkl + all ~24,366 records
        │
        ├─ Predict passengers for every record (train + val + test)
        ├─ Clip predictions to [0, capacity × 1.1]
        ├─ Compute demand thresholds from 33rd/66th percentile of training target
        ├─ Classify: Low / Medium / High demand per prediction
        ├─ Compute recommended_buses = ceil(predicted / BUS_CAPACITY)
        │
        └─ Save: outputs/predictions/demand_predictions.csv
            Columns: prediction_id, date, route, bus_type, transport_mode,
                     actual_demand, predicted_demand, demand_category,
                     prediction_error, recommended_buses, model_name, split
```

#### Single Prediction API

```python
from src.ml.predict import predict_single

result = predict_single(
    route       = "Kurnool-Hyderabad",
    date        = "2024-12-15",
    bus_type    = "Volvo Ac",
    distance_km = 326.0,
    capacity    = 49,
    is_holiday  = 0,
    bus_capacity= 50,
)
# Returns:
# {
#   'predicted_demand'  : 38,
#   'demand_category'   : 'Medium',
#   'recommended_buses' : 1,
#   'model_name'        : 'CatBoostRegressor'
# }
```

---

## 4. Data Flow Summary

```
datasets/ (3 raw CSVs)
    │
    ▼ Step 1: ETL
data/processed/ (4 clean CSVs)
    │
    ├──────────────────────────────────────┐
    ▼                                      ▼
Step 2: MySQL DW                    Step 3: Mining
transport_dw database               route_clusters.csv
(OLAP queries)                      transport_anomalies.csv
                                           │
                                           ▼
                                    Step 4: ML Training
                                    best_model.pkl
                                    model_metrics.csv
                                           │
                                           ▼
                                    Step 5: Tuning
                                    tuned_model.pkl (if better)
                                           │
                                           ▼
                                    Step 6: SHAP
                                    shap_*.png
                                    shap_feature_importance.csv
                                           │
                                           ▼
                                    Step 7: Predict
                                    demand_predictions.csv
```

---

## 5. Running Individual Modules Directly

Any module can be run standalone for debugging:

```bash
# ETL
python src/etl/apsrtc.py
python src/etl/railways.py
python src/etl/flights.py

# Mining
python src/mining/clustering.py
python src/mining/anomaly_detection.py

# ML
python src/ml/preprocessing.py   # prints split sizes and feature list
python src/ml/train.py
python src/ml/tune.py
python src/ml/explain.py
python src/ml/predict.py
```

---

## 6. Running Tests

```bash
python tests/test_pipeline.py
```

Verifies:
- Data loading from all 3 datasets
- Preprocessing — no null targets, no negatives
- Feature engineering columns present
- No data leakage in time-aware split (test dates > val dates > train dates)
- Model loads and predicts numeric values
- Prediction pipeline returns valid output structure

---

## 7. Environment Variables Reference

Copy `.env.example` to `.env` before running:

| Variable | Default | Description |
|---|---|---|
| `DB_HOST` | `localhost` | MySQL host |
| `DB_PORT` | `3306` | MySQL port |
| `DB_NAME` | `transport_dw` | Database name |
| `DB_USER` | `root` | MySQL username |
| `DB_PASSWORD` | `` | MySQL password |
| `DATA_RAW_DIR` | `data/raw` | Raw data location |
| `DATA_PROCESSED_DIR` | `data/processed` | Processed data output |
| `MODELS_DIR` | `models` | Model save location |
| `OUTPUTS_DIR` | `outputs` | Outputs root |
| `RANDOM_SEED` | `42` | Global random seed |
| `TEST_SIZE` | `0.15` | Test split fraction |
| `VAL_SIZE` | `0.15` | Validation split fraction |
| `BUS_CAPACITY` | `50` | Default bus capacity for fleet sizing |

---

## 8. Common Issues and Fixes

| Issue | Cause | Fix |
|---|---|---|
| `FileNotFoundError: apsrtc_features.csv` | ETL not run yet | Run `--steps etl` first |
| `FileNotFoundError: best_model.pkl` | Training not run | Run `--steps train` first |
| `DW load skipped (MySQL may not be configured)` | MySQL not running or credentials wrong | Check `.env` or skip `load_dw` step |
| `No passengers column in railways data` | ETL not run after seeding | Re-run `--steps etl` |
| SHAP slow on large dataset | Large test set | Normal — uses 200-sample subset automatically |
| `ModuleNotFoundError` | Dependencies not installed | Run `pip install -r requirements.txt` |
