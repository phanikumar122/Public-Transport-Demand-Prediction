# Product Requirements Document (PRD)

**Project**: Public Transport Demand Prediction  
**Course**: Data Mining and Data Warehousing (DMDW)  
**Version**: 1.0.0  
**Status**: Active Development

---

## 1. Overview

### 1.1 Problem Statement

Public transport authorities lack accurate tools to forecast passenger demand across bus, rail, and air modes. This leads to:

- Over-deployment of vehicles on low-demand routes, wasting fuel and resources
- Under-deployment on high-demand routes, causing overcrowding
- Inability to proactively manage peak-hour congestion
- Revenue loss due to poor capacity planning

### 1.2 Solution

An end-to-end multi-modal transport analytics and demand prediction system that:

1. Integrates 3 real-world Indian transport datasets into a unified MySQL data warehouse
2. Applies OLAP operations for multi-dimensional analytics
3. Runs K-Means clustering and Isolation Forest anomaly detection across all 3 modes
4. Trains and compares 5 ML regression models on combined ~24,366 rows
5. Explains predictions using SHAP (Explainable AI)
6. Generates demand predictions and vehicle deployment recommendations

---

## 2. Datasets

### 2.1 APSRTC — Bus (`datasets/apstrc.csv`)

| Property | Value |
|---|---|
| Rows | 1,000 |
| Columns | 14 |
| Target | `passengers` (integer count per trip) |
| Date Range | 2024-01-01 → 2024-12-30 |
| Routes | 15 (Kurnool-Hyderabad, Guntur-Hyderabad, etc.) |
| Depots | 7 (Hyderabad, Guntur, Nellore, Kurnool, Visakhapatnam, Tirupati, Vijayawada) |
| Bus Types | Volvo AC, Sleeper, Semi-Sleeper, Super Luxury, Express, Ordinary |
| Missing Values | None |
| Duplicates | None |

### 2.2 IRCTC — Railways (`datasets/Irctc.csv`)

| Property | Value |
|---|---|
| Rows | 8,366 |
| Columns | 11 |
| Target | `passengers` (seeded: train type × distance; min=42, max=760, avg=216) |
| Train Types | Rajdhani, Shatabdi, Duronto, Superfast, Express, Local/MEMU |
| Missing Values | None |
| Duplicates | None |

**Seeding logic**: Rajdhani (300–600) → Shatabdi (200–500) → Express (100–400) → Local/MEMU (50–250), scaled by distance modifier.

### 2.3 Indian Domestic Flights (`datasets/flights.csv`)

| Property | Value |
|---|---|
| Rows | 15,000 |
| Columns | 13 |
| Target | `passengers` (seeded: airline capacity × stops load factor × price; min=11, max=291, avg=83) |
| Airlines | IndiGo, SpiceJet, Air India, Vistara, GoAir, Akasa Air, AirAsia India, Alliance Air, TruJet, Star Air |
| Date Range | 2019–2025 |
| Missing Values | None |
| Duplicates | None |

**Seeding logic**: Airline fleet tier (full-service=250, LCC=160, regional=72) × load factor by stops (non-stop: 75–98%, 3 stops: 30–60%) × price adjustment.

---

## 3. Functional Requirements

### FR-1: ETL Pipeline

| ID | Requirement |
|---|---|
| FR-1.1 | Extract APSRTC CSV, clean, and engineer 30+ features |
| FR-1.2 | Extract IRCTC CSV, parse times, classify train types, expand class flags |
| FR-1.3 | Extract Flights CSV, parse duration, stops, encode airline tiers |
| FR-1.4 | Save 4 processed CSVs to `data/processed/` |
| FR-1.5 | All ETL steps must be idempotent and re-runnable |
| FR-1.6 | Pipeline fallback: read from `datasets/` if `data/raw/` is absent |

### FR-2: Data Warehouse

| ID | Requirement |
|---|---|
| FR-2.1 | Build MySQL star schema with 4 dimension tables and 1 central fact table |
| FR-2.2 | Load all 3 datasets into `fact_transport` with `source_dataset` tag |
| FR-2.3 | Implement Roll-up, Drill-down, Slice, and Dice OLAP operations in SQL |
| FR-2.4 | Populate `dim_date` with calendar dates 2019–2026 including holiday flags |
| FR-2.5 | DW load must be skippable/optional if MySQL is not configured |

### FR-3: Data Mining

| ID | Requirement |
|---|---|
| FR-3.1 | K-Means clustering must run on routes from all 3 transport modes |
| FR-3.2 | Optimal K must be auto-selected via Elbow + Silhouette score |
| FR-3.3 | Clusters must be labelled: Low / Medium / High Demand / Peak-Dependent |
| FR-3.4 | Isolation Forest must detect anomalies across all 3 datasets |
| FR-3.5 | Anomaly detection must report per-mode breakdown in logs |
| FR-3.6 | Outputs: `route_clusters.csv`, `transport_anomalies.csv` |

### FR-4: Machine Learning

| ID | Requirement |
|---|---|
| FR-4.1 | Train on unified dataset of all 3 modes (~24,366 rows) |
| FR-4.2 | Use time-aware chronological split: Train 70% / Val 15% / Test 15% — no shuffling |
| FR-4.3 | Train 5 models: Ridge, Random Forest, XGBoost, LightGBM, CatBoost |
| FR-4.4 | Select best model by lowest validation MAE (not test MAE) |
| FR-4.5 | Report MAE, RMSE, MAPE, R² for both val and test splits |
| FR-4.6 | Prevent all forms of data leakage (post-trip columns excluded, lag features shifted) |
| FR-4.7 | Save `best_model.pkl`, `all_models.pkl`, `model_metadata.json` |

### FR-5: Hyperparameter Tuning

| ID | Requirement |
|---|---|
| FR-5.1 | Tune XGBoost, LightGBM, CatBoost via RandomizedSearchCV |
| FR-5.2 | Use TimeSeriesSplit (5 folds) for CV — no future leakage |
| FR-5.3 | Replace `best_model.pkl` only if tuned model improves CV MAE |
| FR-5.4 | Save `tuned_model.pkl` and `tuned_model_metadata.json` |

### FR-6: Explainability (SHAP)

| ID | Requirement |
|---|---|
| FR-6.1 | Compute SHAP values for the best model on the test set |
| FR-6.2 | Generate 3 charts: global importance bar, beeswarm summary, waterfall (single prediction) |
| FR-6.3 | Save `shap_feature_importance.csv` and `shap_values.csv` |

### FR-7: Prediction Pipeline

| ID | Requirement |
|---|---|
| FR-7.1 | Generate batch predictions for all ~24,366 records |
| FR-7.2 | Classify each prediction as Low / Medium / High demand (33rd/66th percentile thresholds) |
| FR-7.3 | Compute `recommended_buses = ceil(predicted_demand / bus_capacity)` |
| FR-7.4 | Support single-trip prediction via `predict_single()` API |
| FR-7.5 | Save `demand_predictions.csv` |

---

## 4. Non-Functional Requirements

| Category | Requirement |
|---|---|
| **Reproducibility** | `python run_pipeline.py` must produce deterministic outputs (all random seeds fixed at 42) |
| **Modularity** | Each step (etl / load_dw / mine / train / tune / explain / predict) must run independently |
| **No Data Leakage** | Post-trip columns (`occupancy_rate`, `revenue`, `fuel_consumed_liters`) excluded from ML features |
| **Performance** | Full pipeline must complete within 30 minutes on a standard laptop |
| **Logging** | All steps must log progress, row counts, and key metrics to console |
| **Fault Tolerance** | MySQL unavailability must not break the ETL, mining, or ML steps |

---

## 5. Feature Engineering Requirements

### 5.1 APSRTC Features (computed in `src/etl/apsrtc.py`)

| Category | Features |
|---|---|
| Temporal | `year`, `month_num`, `day_num`, `dow`, `is_weekend`, `quarter`, `week_of_year`, `is_holiday` |
| Lag (route-grouped, shifted) | `lag_1`, `lag_7` |
| Rolling (route-grouped, shifted) | `rolling_mean_7`, `rolling_mean_14`, `rolling_max_7`, `rolling_min_7`, `rolling_std_7` |
| Historical means (leakage-free) | `route_hist_mean`, `bustype_hist_mean`, `route_month_mean`, `route_bustype_mean` |
| Encodings | `route_encoded`, `bus_type_encoded`, `depot_encoded` |

### 5.2 Unified ML Features (computed in `src/ml/preprocessing.py`)

All 3 datasets are normalised to a shared 27-feature space:

| Feature | Description |
|---|---|
| `transport_mode_encoded` | 0=Bus, 1=Rail, 2=Air |
| `capacity` | Bus seats / rail coaches proxy / flight seats |
| `distance_km` | Route distance (derived for flights from `duration_minutes × 8.5`) |
| `fare_per_passenger` | Ticket price (fare for bus/rail, price for flights) |
| `mode_type_encoded` | bus_type / train_type / airline (encoded) |
| `operator_encoded` | depot / train_name / airline (encoded) |

### 5.3 Leakage-Excluded Columns

The following are **never** used as ML features:

- `occupancy_rate` — derived from `passengers / capacity × 100`
- `revenue` — derived from `passengers × fare`
- `fuel_consumed_liters` — post-trip measurement
- `seats_remaining` — derived from `capacity − passengers`

---

## 6. Output Artifacts

| Artifact | Path | Consumer |
|---|---|---|
| Cleaned APSRTC | `data/processed/apsrtc_clean.csv` | ML, Mining, DW |
| Feature-engineered APSRTC | `data/processed/apsrtc_features.csv` | ML |
| Cleaned Railways | `data/processed/railways_clean.csv` | ML, Mining, DW |
| Cleaned Flights | `data/processed/flights_clean.csv` | ML, Mining, DW |
| Best ML model | `models/best_model.pkl` | Predictions |
| All models | `models/all_models.pkl` | Evaluation |
| Model metadata | `models/model_metadata.json` | Reporting |
| Tuned model | `models/tuned_model.pkl` | Predictions |
| Model metrics | `outputs/metrics/model_metrics.csv` | Analysis |
| SHAP importance | `outputs/metrics/shap_feature_importance.csv` | Analysis |
| SHAP values | `outputs/metrics/shap_values.csv` | Analysis |
| Demand predictions | `outputs/predictions/demand_predictions.csv` | Analysis |
| Route clusters | `outputs/predictions/route_clusters.csv` | Analysis |
| Transport anomalies | `outputs/predictions/transport_anomalies.csv` | Analysis |
| SHAP charts (3 PNGs) | `reports/figures/shap_*.png` | Reports |
| Cluster charts | `outputs/figures/kmeans_*.png` | Reports |
| Anomaly charts | `outputs/figures/anomaly_*.png` | Reports |
| Model comparison chart | `outputs/figures/model_comparison.png` | Reports |

---

## 7. Constraints and Limitations

| Constraint | Detail |
|---|---|
| APSRTC size | 1,000 rows — sufficient for academic demonstration, not production scale |
| IRCTC passengers | Seeded values, not real survey data |
| Flights passengers | Seeded values derived from load factor heuristics |
| IRCTC dates | Synthetic 2019–2024 random dates (no actual service dates in the dataset) |
| Holiday calendar | Approximate — uses 9 fixed Indian national holiday dates |
| Lag features | ~66 records per APSRTC route — limited lag depth |
| MySQL optional | DW load step skips gracefully if MySQL not configured |

---

## 8. Success Criteria

| Metric | Target |
|---|---|
| ETL completion | All 3 datasets processed with 0 missing values in output |
| ML training | All 5 models train and report metrics without errors |
| Best model R² | > 0.15 on test set (small dataset expectation) |
| Prediction coverage | All ~24,366 records get a predicted demand value |
| Anomaly detection | ~5% flagged per mode (contamination=0.05) |
| Pipeline reproducibility | Same results on every run with fixed `RANDOM_SEED=42` |
| Output completeness | All CSV and PNG artifacts generated successfully |
