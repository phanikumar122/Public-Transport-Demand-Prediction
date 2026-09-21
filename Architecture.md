# System Architecture

**Project**: Public Transport Demand Prediction  
**Stack**: Python 3.x · MySQL 8 · Scikit-learn · XGBoost · LightGBM · CatBoost · SHAP

---

## 1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         RAW DATA LAYER                              │
│                                                                     │
│   datasets/apstrc.csv     datasets/Irctc.csv    datasets/flights.csv│
│   (APSRTC Bus — 1,000)    (Rail — 8,366)        (Air — 15,000)     │
└───────────────┬───────────────────┬──────────────────┬─────────────┘
                │                   │                  │
                ▼                   ▼                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          ETL LAYER                                  │
│                                                                     │
│   src/etl/apsrtc.py      src/etl/railways.py   src/etl/flights.py  │
│   ─────────────────       ─────────────────    ────────────────     │
│   • Normalise columns     • Parse times        • Parse duration     │
│   • Date parsing          • Classify train     • Parse stops        │
│   • Outlier clipping        type               • Airline tier       │
│   • Feature engineering   • Class flags        • Temporal features  │
│   • Lag + rolling         • Passengers col     • Passengers col     │
│     features              • Temporal feats     • Route encoding     │
│                                                                     │
│              └─────────────────┬───────────────────┘               │
│                                ▼                                    │
│                    src/etl/pipeline.py                              │
│                    (orchestrates all 3 ETL runs)                    │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
              ┌───────────────┴──────────────────┐
              ▼                                  ▼
┌─────────────────────────┐       ┌──────────────────────────────────┐
│    DATA WAREHOUSE LAYER │       │         ANALYTICS LAYER          │
│                         │       │                                  │
│  MySQL: transport_dw    │       │   src/mining/clustering.py       │
│  ─────────────────────  │       │   ──────────────────────────     │
│  dim_date               │       │   • Load all 3 processed CSVs    │
│  dim_route              │       │   • Build route feature matrix   │
│  dim_transport_mode     │       │   • StandardScaler               │
│  dim_location           │       │   • Elbow + Silhouette → best K  │
│  fact_transport         │       │   • KMeans (n_init=20)           │
│  fact_predictions       │       │   • Label clusters by demand     │
│  ml_model_metrics       │       │   • Save route_clusters.csv      │
│  mining_clusters        │       │                                  │
│  mining_anomalies       │       │   src/mining/anomaly_detection.py│
│                         │       │   ────────────────────────────── │
│  OLAP Queries:          │       │   • Load all 3 processed CSVs    │
│  • Roll-up              │       │   • StandardScaler               │
│  • Drill-down           │       │   • IsolationForest              │
│  • Slice                │       │     (contamination=0.05)         │
│  • Dice                 │       │   • Per-mode anomaly breakdown   │
│                         │       │   • Save transport_anomalies.csv │
└─────────────────────────┘       └──────────────────────────────────┘
                                                 │
                              ┌──────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        ML LAYER                                     │
│                                                                     │
│   src/ml/preprocessing.py                                          │
│   ─────────────────────────────────────────────────────────────    │
│   • _load_apsrtc()  → unified schema (transport_mode_encoded=0)    │
│   • _load_railways()→ unified schema (transport_mode_encoded=1)    │
│   • _load_flights() → unified schema (transport_mode_encoded=2)    │
│   • concat → ~24,366 rows                                          │
│   • Shared lag/rolling/historical features (shift(1), no leakage) │
│   • Time-aware split: TRAIN 70% / VAL 15% / TEST 15%              │
│   • NaN fill from training statistics only                         │
│                                                                     │
│   src/ml/train.py                                                  │
│   ─────────────────────────────────────────────────────────────    │
│   • Ridge (baseline)                                               │
│   • RandomForest (n_estimators=500, max_depth=8)                  │
│   • XGBoost (early stopping, eval on val set)                      │
│   • LightGBM (early stopping, eval on val set)                     │
│   • CatBoost (early stopping, eval on val set)                     │
│   • Select best by lowest VAL MAE                                  │
│                                                                     │
│   src/ml/tune.py                                                   │
│   ─────────────────────────────────────────────────────────────    │
│   • RandomizedSearchCV (n_iter=25)                                 │
│   • TimeSeriesSplit (5 folds)                                      │
│   • Tune: XGBoost / LightGBM / CatBoost / RandomForest            │
│   • Replace best_model.pkl only if CV MAE improves                │
│                                                                     │
│   src/ml/explain.py                                                │
│   ─────────────────────────────────────────────────────────────    │
│   • SHAP TreeExplainer (test set sample, n=200)                    │
│   • Global importance bar chart                                    │
│   • Beeswarm summary plot                                          │
│   • Waterfall (single prediction)                                  │
│                                                                     │
│   src/ml/predict.py                                                │
│   ─────────────────────────────────────────────────────────────    │
│   • Batch predictions: all ~24,366 records                         │
│   • demand_category: Low / Medium / High (33rd/66th percentile)   │
│   • recommended_buses = ceil(predicted_demand / bus_capacity)      │
│   • predict_single() API for individual trip queries               │
└─────────────────────────┬───────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       OUTPUT LAYER                                  │
│                                                                     │
│   outputs/predictions/demand_predictions.csv   → Analysis          │
│   outputs/predictions/route_clusters.csv       → Analysis          │
│   outputs/predictions/transport_anomalies.csv  → Analysis          │
│   outputs/metrics/model_metrics.csv            → Analysis          │
│   outputs/metrics/shap_feature_importance.csv  → Reports           │
│   outputs/figures/*.png                        → Report charts     │
│   reports/figures/shap_*.png                   → SHAP charts       │
│   models/best_model.pkl                        → predict_single()  │
│   MySQL: transport_dw                          → OLAP queries      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Directory Structure

```
public-transport-demand-prediction/
│
├── datasets/                        ← Raw source files
│   ├── apstrc.csv                   (APSRTC bus data, 1,000 rows)
│   ├── Irctc.csv                    (Indian Railways, 8,366 rows)
│   └── flights.csv                  (Domestic flights, 15,000 rows)
│
├── data/
│   ├── raw/                         ← ETL reads from here
│   │   ├── apsrtc/APSRTC_Transport_Data.csv
│   │   ├── railways/IRCTC_cleaned.csv
│   │   └── flights/flights.csv
│   └── processed/                   ← ETL writes cleaned CSVs here
│       ├── apsrtc_clean.csv
│       ├── apsrtc_features.csv
│       ├── railways_clean.csv
│       └── flights_clean.csv
│
├── src/
│   ├── config.py                    ← All paths, DB config, ML params
│   ├── etl/
│   │   ├── apsrtc.py                ← APSRTC ETL + feature engineering
│   │   ├── railways.py              ← Railways ETL
│   │   ├── flights.py               ← Flights ETL
│   │   └── pipeline.py              ← Runs all 3 ETLs
│   ├── warehouse/
│   │   ├── schema.sql               ← Star schema DDL
│   │   ├── load.py                  ← Python → MySQL loader
│   │   └── queries.sql              ← OLAP queries (Roll-up/Drill-down/Slice/Dice)
│   ├── mining/
│   │   ├── clustering.py            ← K-Means (all 3 modes)
│   │   └── anomaly_detection.py     ← Isolation Forest (all 3 modes)
│   ├── ml/
│   │   ├── preprocessing.py         ← Merge 3 datasets + feature prep + split
│   │   ├── train.py                 ← Train 5 models + compare
│   │   ├── evaluate.py              ← MAE/RMSE/MAPE/R² + charts
│   │   ├── tune.py                  ← RandomizedSearchCV + TimeSeriesSplit
│   │   ├── explain.py               ← SHAP analysis
│   │   └── predict.py               ← Batch + single predictions
│   └── utils/
│       └── logger.py                ← Unified logger
│
├── models/
│   ├── best_model.pkl               ← Best trained model
│   ├── all_models.pkl               ← All 5 trained models
│   ├── tuned_model.pkl              ← Best hyperparameter-tuned model
│   ├── model_metadata.json          ← Metrics + feature list
│   └── tuned_model_metadata.json
│
├── outputs/
│   ├── predictions/
│   │   ├── demand_predictions.csv
│   │   ├── route_clusters.csv
│   │   └── transport_anomalies.csv
│   ├── metrics/
│   │   ├── model_metrics.csv
│   │   ├── tuned_model_metrics.csv
│   │   ├── shap_feature_importance.csv
│   │   └── shap_values.csv
│   └── figures/
│       ├── kmeans_elbow_silhouette.png
│       ├── kmeans_clusters.png
│       ├── anomaly_detection.png
│       ├── anomaly_by_mode.png
│       └── model_comparison.png
│
├── reports/figures/
│   ├── shap_global_importance.png
│   ├── shap_summary_plot.png
│   └── shap_waterfall_single.png
│
├── notebooks/                       ← Jupyter EDA notebooks (01–06)
├── tests/test_pipeline.py
├── run_pipeline.py                  ← Master entry point
├── requirements.txt
├── .env.example
├── PRD.md
├── Architecture.md
├── Workflow.md
└── README.md
```

---

## 3. Data Warehouse Schema

```
                          dim_date
                         (date_key PK)
                         year, quarter, month, day
                         is_weekend, is_holiday
                              │
                              │ FK
                              │
dim_route ─────────── fact_transport ──────────── dim_transport_mode
(route_key PK)        (fact_id PK)               (mode_key PK)
route_name            date_key   FK              mode_name (Bus/Rail/Flight)
source_city           route_key  FK              sub_type
destination_city      mode_key   FK              operator
                      location_key FK
                      passenger_count
                      capacity                     dim_location
                      occupancy_rate         ──── (location_key PK)
                      distance_km                 location_name
                      revenue                     location_type
                      fare_per_passenger          city, state
                      price
                      duration_minutes
                      num_stops
                      source_dataset

           ┌──────────────────────────────────────────────┐
           │           Analytics Tables                   │
           │                                              │
           │  fact_predictions    ml_model_metrics        │
           │  mining_clusters     mining_anomalies        │
           └──────────────────────────────────────────────┘
```

---

## 4. ML Pipeline Architecture

### 4.1 Unified Feature Schema

All 3 datasets are normalised to 27 shared features before training:

```
Pre-trip operational:
  capacity · distance_km · fare_per_passenger · transport_mode_encoded

Temporal (8 features):
  year · month_num · day_num · dow · is_weekend · quarter · week_of_year · is_holiday

Lag & Rolling (7 features, all shifted by 1 — no leakage):
  lag_1 · lag_7
  rolling_mean_7 · rolling_mean_14 · rolling_max_7 · rolling_min_7 · rolling_std_7

Historical means (4 features, expanding mean shifted by 1):
  route_hist_mean · modetype_hist_mean · route_month_mean · route_modetype_mean

Categorical encodings (3 features):
  route_encoded · mode_type_encoded · operator_encoded
```

### 4.2 Time-Aware Split

```
All records sorted chronologically (by date)
─────────────────────────────────────────────────────────────────► time

│◄──────── TRAIN (70%) ─────────►│◄── VAL (15%) ──►│◄── TEST (15%) ──►│
│  ~17,056 rows                  │  ~3,655 rows    │  ~3,655 rows     │
│  Oldest dates                  │                 │  Newest dates    │

- No shuffling at any stage
- NaN fill statistics computed from TRAIN only → applied to VAL and TEST
- Early stopping for XGBoost/LightGBM/CatBoost uses VAL set
- Best model selection uses VAL MAE (test set untouched until final eval)
```

### 4.3 Model Comparison

| Model | Key Config |
|---|---|
| Ridge | alpha=1.0 |
| Random Forest | n_estimators=500, max_depth=8, min_samples_leaf=4 |
| XGBoost | n_estimators=1000 (early stop), max_depth=4, lr=0.02 |
| LightGBM | n_estimators=1000 (early stop), num_leaves=31, lr=0.02 |
| CatBoost | iterations=1000 (early stop), depth=5, l2_leaf_reg=5 |

---

## 5. Technology Stack

| Component | Technology | Purpose |
|---|---|---|
| Language | Python 3.x | All ETL, mining, ML, prediction |
| Data processing | Pandas, NumPy | Data manipulation and feature engineering |
| ML models | Scikit-learn, XGBoost, LightGBM, CatBoost | Model training and evaluation |
| Explainability | SHAP | Feature importance and prediction explanation |
| Visualisation | Matplotlib, Seaborn | Pipeline output charts |
| Database | MySQL 8 | Star-schema data warehouse |
| ORM / DB driver | SQLAlchemy, PyMySQL | Python ↔ MySQL connectivity |
| Config | python-dotenv | Environment variables |
| Serialisation | Joblib | Model save/load |
| Orchestration | `run_pipeline.py` | Single-command end-to-end execution |

---

## 6. Environment Configuration

All configurable values live in `.env` (copied from `.env.example`):

```ini
# Database
DB_HOST=localhost
DB_PORT=3306
DB_NAME=transport_dw
DB_USER=root
DB_PASSWORD=

# Paths (override defaults from config.py)
DATA_RAW_DIR=data/raw
DATA_PROCESSED_DIR=data/processed
MODELS_DIR=models
OUTPUTS_DIR=outputs

# ML settings
RANDOM_SEED=42
TEST_SIZE=0.15
VAL_SIZE=0.15
BUS_CAPACITY=50
```
