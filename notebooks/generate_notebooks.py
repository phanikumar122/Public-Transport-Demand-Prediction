"""
notebooks/generate_notebooks.py — Creates all 6 Jupyter notebooks for the project.
Run once to generate the .ipynb files.
"""

import json
import pathlib
import sys

NB_DIR = pathlib.Path(__file__).parent
ROOT = NB_DIR.parent


def nb(cells):
    return {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            },
            "language_info": {
                "name": "python",
                "version": "3.11"
            }
        },
        "cells": cells
    }


def md(src, idx=0):
    return {"cell_type": "markdown", "metadata": {}, "source": src, "id": f"md_{idx}"}


def code(src, idx=0):
    return {
        "cell_type": "code",
        "metadata": {},
        "source": src,
        "outputs": [],
        "execution_count": None,
        "id": f"c_{idx}"
    }


# ─────────────────────────────────────────────────────────────────────────────
# NB 1 — Data Inspection
# ─────────────────────────────────────────────────────────────────────────────
nb1 = nb([
    md("# 01 — Data Inspection\nLoad and inspect all three raw datasets.", 0),
    code(
        "import sys, zipfile, pathlib\n"
        "sys.path.insert(0, str(pathlib.Path('.').resolve().parent))\n"
        "import pandas as pd\n\n"
        "ZIP_ROOT = str(pathlib.Path('..').resolve().parent)\n\n"
        "with zipfile.ZipFile(f'{ZIP_ROOT}/apsrtc.zip') as z:\n"
        "    with z.open('APSRTC_Transport_Data.csv') as f:\n"
        "        apsrtc = pd.read_csv(f)\n\n"
        "print(f'APSRTC Shape: {apsrtc.shape}')\n"
        "apsrtc.head()",
        1
    ),
    code(
        "print('Dtypes:\\n', apsrtc.dtypes)\n"
        "print('\\nMissing values:\\n', apsrtc.isnull().sum())",
        2
    ),
    code("apsrtc.describe()", 3),
    code(
        "with zipfile.ZipFile(f'{ZIP_ROOT}/domestic flights.zip') as z:\n"
        "    with z.open('flights.csv') as f:\n"
        "        flights = pd.read_csv(f)\n"
        "print(f'Flights Shape: {flights.shape}')\n"
        "flights.head()",
        4
    ),
    code(
        "with zipfile.ZipFile(f'{ZIP_ROOT}/irctc.zip') as z:\n"
        "    with z.open('IRCTC_cleaned.csv') as f:\n"
        "        railways = pd.read_csv(f)\n"
        "print(f'Railways Shape: {railways.shape}')\n"
        "railways.head()",
        5
    ),
    md(
        "## Data Dictionary\n\n"
        "### APSRTC (ML TARGET = `passengers`)\n\n"
        "| Column | Type | Description |\n"
        "|--------|------|-------------|\n"
        "| route | str | Origin–Destination pair |\n"
        "| bus_type | str | Service class (Volvo AC, Sleeper…) |\n"
        "| depot | str | Operating depot |\n"
        "| date | date | Trip date |\n"
        "| capacity | int | Seat capacity |\n"
        "| **passengers** | **int** | **TARGET — passengers carried** |\n"
        "| occupancy_rate | float | % seats filled (POST-TRIP) |\n"
        "| distance_km | float | Route distance |\n"
        "| fare_per_passenger | float | Ticket fare |\n"
        "| revenue | float | Trip revenue (POST-TRIP) |\n",
        6
    ),
])

with open(NB_DIR / "01_data_inspection.ipynb", "w", encoding="utf-8") as f:
    json.dump(nb1, f, indent=1)

# ─────────────────────────────────────────────────────────────────────────────
# NB 2 — EDA
# ─────────────────────────────────────────────────────────────────────────────
nb2 = nb([
    md("# 02 — Exploratory Data Analysis (EDA)\nAnalyse APSRTC patterns, distributions, correlations.", 0),
    code(
        "import sys, pathlib\n"
        "sys.path.insert(0, str(pathlib.Path('..').resolve()))\n"
        "import pandas as pd\n"
        "import numpy as np\n"
        "import matplotlib.pyplot as plt\n"
        "import seaborn as sns\n"
        "%matplotlib inline\n\n"
        "df = pd.read_csv('../data/processed/apsrtc_features.csv')\n"
        "df['date'] = pd.to_datetime(df['date'], errors='coerce')\n"
        "print(f'Shape: {df.shape}')\n"
        "df.head()",
        1
    ),
    code(
        "# Demand distribution\n"
        "fig, axes = plt.subplots(1, 2, figsize=(14, 5))\n"
        "axes[0].hist(df['passengers'], bins=30, color='steelblue', edgecolor='white')\n"
        "axes[0].set_title('Demand Distribution')\n"
        "axes[0].set_xlabel('Passengers per Trip')\n"
        "axes[1].boxplot(df['passengers'], vert=False)\n"
        "axes[1].set_title('Box Plot')\n"
        "plt.tight_layout()\n"
        "plt.savefig('../reports/figures/demand_distribution.png', dpi=150)\n"
        "plt.show()",
        2
    ),
    code(
        "# Average demand by route\n"
        "route_demand = df.groupby('route')['passengers'].mean().sort_values(ascending=False)\n"
        "plt.figure(figsize=(14, 6))\n"
        "route_demand.plot(kind='bar', color='steelblue', alpha=0.85)\n"
        "plt.title('Average Passengers by Route', fontsize=14, fontweight='bold')\n"
        "plt.xticks(rotation=45, ha='right')\n"
        "plt.ylabel('Average Passengers')\n"
        "plt.tight_layout()\n"
        "plt.savefig('../reports/figures/demand_by_route.png', dpi=150)\n"
        "plt.show()",
        3
    ),
    code(
        "# Demand by day of week\n"
        "dow_demand = df.groupby('dow')['passengers'].mean()\n"
        "plt.figure(figsize=(10, 5))\n"
        "plt.bar(range(7), dow_demand.values, color='coral')\n"
        "plt.xticks(range(7), ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'])\n"
        "plt.title('Average Demand by Day of Week')\n"
        "plt.ylabel('Avg Passengers')\n"
        "plt.tight_layout()\n"
        "plt.savefig('../reports/figures/demand_by_dow.png', dpi=150)\n"
        "plt.show()",
        4
    ),
    code(
        "# Monthly trend\n"
        "monthly = df.resample('ME', on='date')['passengers'].mean()\n"
        "plt.figure(figsize=(14, 5))\n"
        "plt.plot(monthly.index, monthly.values, 'bo-', linewidth=2)\n"
        "plt.fill_between(monthly.index, monthly.values, alpha=0.3)\n"
        "plt.title('Monthly Average Demand Trend')\n"
        "plt.tight_layout()\n"
        "plt.savefig('../reports/figures/demand_trend.png', dpi=150)\n"
        "plt.show()",
        5
    ),
    code(
        "# Correlation heatmap\n"
        "nums = ['passengers','capacity','distance_km','fare_per_passenger','lag_1','lag_7','rolling_mean_7']\n"
        "corr = df[nums].corr()\n"
        "plt.figure(figsize=(10, 8))\n"
        "sns.heatmap(corr, annot=True, fmt='.2f', cmap='coolwarm', center=0, square=True)\n"
        "plt.title('Correlation Heatmap')\n"
        "plt.tight_layout()\n"
        "plt.savefig('../reports/figures/correlation_heatmap.png', dpi=150)\n"
        "plt.show()",
        6
    ),
    code(
        "# Weekend vs Weekday\n"
        "wkd = df.groupby('is_weekend')['passengers'].mean()\n"
        "plt.figure(figsize=(6, 5))\n"
        "plt.bar(['Weekday','Weekend'], wkd.values, color=['steelblue','coral'])\n"
        "plt.title('Average Demand: Weekday vs Weekend')\n"
        "plt.ylabel('Average Passengers')\n"
        "for i, v in enumerate(wkd.values):\n"
        "    plt.text(i, v + 0.3, f'{v:.1f}', ha='center', fontweight='bold')\n"
        "plt.tight_layout()\n"
        "plt.savefig('../reports/figures/weekday_vs_weekend.png', dpi=150)\n"
        "plt.show()",
        7
    ),
])

with open(NB_DIR / "02_eda.ipynb", "w", encoding="utf-8") as f:
    json.dump(nb2, f, indent=1)

# ─────────────────────────────────────────────────────────────────────────────
# NB 3 — OLAP
# ─────────────────────────────────────────────────────────────────────────────
nb3 = nb([
    md("# 03 — OLAP Analysis\nRoll-up, Drill-down, Slice, and Dice operations.", 0),
    code(
        "import sys, pathlib\n"
        "sys.path.insert(0, str(pathlib.Path('..').resolve()))\n"
        "import pandas as pd\n"
        "import matplotlib.pyplot as plt\n"
        "%matplotlib inline\n\n"
        "df = pd.read_csv('../data/processed/apsrtc_features.csv')\n"
        "df['date'] = pd.to_datetime(df['date'], errors='coerce')\n"
        "print('Shape:', df.shape)",
        1
    ),
    code(
        "# ROLL-UP: monthly aggregation\n"
        "print('=== ROLL-UP: Monthly Demand ===')\n"
        "monthly = df.groupby(['year','month_num'])['passengers'].agg(['sum','mean','count'])\n"
        "monthly.columns = ['total_passengers','avg_passengers','trips']\n"
        "print(monthly.to_string())",
        2
    ),
    code(
        "# DRILL-DOWN: 2024 by month\n"
        "print('=== DRILL-DOWN: 2024 Month-by-Month ===')\n"
        "y2024 = df[df['year'] == 2024].groupby('month_num')['passengers'].sum()\n"
        "y2024.plot(kind='bar', title='2024 Monthly Total Passengers', figsize=(10, 4))\n"
        "plt.tight_layout()\n"
        "plt.show()",
        3
    ),
    code(
        "# SLICE: Volvo AC only\n"
        "print('=== SLICE: Volvo AC ===')\n"
        "volvo = df[df['bus_type'].str.contains('Volvo', case=False, na=False)]\n"
        "print(f'Volvo trips: {len(volvo)}')\n"
        "print(volvo.groupby('route')['passengers'].mean().sort_values(ascending=False))",
        4
    ),
    code(
        "# DICE: August + Weekday\n"
        "print('=== DICE: August Weekdays ===')\n"
        "aug_wkd = df[(df['month_num'] == 8) & (df['is_weekend'] == 0)]\n"
        "result = aug_wkd.groupby('route')['passengers'].agg(['mean','count'])\n"
        "result.columns = ['avg_passengers','trips']\n"
        "print(result.sort_values('avg_passengers', ascending=False))",
        5
    ),
    code(
        "# KPI summary\n"
        "kpis = {\n"
        "    'Total Routes':    df['route'].nunique(),\n"
        "    'Total Trips':     len(df),\n"
        "    'Total Passengers': int(df['passengers'].sum()),\n"
        "    'Avg Demand/Trip':  round(df['passengers'].mean(), 1),\n"
        "    'Peak Demand':     int(df['passengers'].max()),\n"
        "    'Min Demand':      int(df['passengers'].min()),\n"
        "    'Avg Revenue/Trip': round(df['revenue'].mean(), 0),\n"
        "}\n"
        "for k, v in kpis.items():\n"
        "    print(f'{k:25s}: {v}')",
        6
    ),
])

with open(NB_DIR / "03_olap_analysis.ipynb", "w", encoding="utf-8") as f:
    json.dump(nb3, f, indent=1)

# ─────────────────────────────────────────────────────────────────────────────
# NB 4 — K-Means
# ─────────────────────────────────────────────────────────────────────────────
nb4 = nb([
    md("# 04 — K-Means Route Clustering\nCluster APSRTC routes by demand characteristics.", 0),
    code(
        "import sys, pathlib\n"
        "sys.path.insert(0, str(pathlib.Path('..').resolve()))\n"
        "from src.mining.clustering import run\n"
        "cluster_df = run()\n"
        "cluster_df[['route','cluster_name','avg_passengers','avg_revenue','avg_occupancy']]"
        ".sort_values('cluster_name')",
        1
    ),
    code(
        "import matplotlib.pyplot as plt\n"
        "from PIL import Image\n"
        "img = Image.open('../reports/figures/kmeans_elbow_silhouette.png')\n"
        "plt.figure(figsize=(14, 5))\n"
        "plt.imshow(img)\n"
        "plt.axis('off')\n"
        "plt.title('Elbow + Silhouette Method for K Selection')\n"
        "plt.show()",
        2
    ),
    code(
        "img2 = Image.open('../reports/figures/kmeans_clusters.png')\n"
        "plt.figure(figsize=(14, 6))\n"
        "plt.imshow(img2)\n"
        "plt.axis('off')\n"
        "plt.title('K-Means Route Clusters')\n"
        "plt.show()",
        3
    ),
])

with open(NB_DIR / "04_kmeans.ipynb", "w", encoding="utf-8") as f:
    json.dump(nb4, f, indent=1)

# ─────────────────────────────────────────────────────────────────────────────
# NB 5 — Anomaly Detection
# ─────────────────────────────────────────────────────────────────────────────
nb5 = nb([
    md("# 05 — Anomaly Detection\nIsolation Forest on APSRTC trip data.", 0),
    code(
        "import sys, pathlib\n"
        "sys.path.insert(0, str(pathlib.Path('..').resolve()))\n"
        "from src.mining.anomaly_detection import run\n"
        "anom_df = run()\n"
        "n_anom = anom_df['is_anomaly'].sum()\n"
        "print(f'Total records: {len(anom_df)}')\n"
        "print(f'Anomalies: {n_anom} ({n_anom/len(anom_df)*100:.1f}%)')\n"
        "anom_df[anom_df['is_anomaly'] == 1].head()",
        1
    ),
    code(
        "import matplotlib.pyplot as plt\n"
        "from PIL import Image\n"
        "img = Image.open('../reports/figures/anomaly_detection.png')\n"
        "plt.figure(figsize=(14, 6))\n"
        "plt.imshow(img)\n"
        "plt.axis('off')\n"
        "plt.title('Anomaly Detection — Isolation Forest')\n"
        "plt.show()",
        2
    ),
    code(
        "print('Top routes with anomalies:')\n"
        "print(anom_df[anom_df['is_anomaly'] == 1].groupby('route').size()\n"
        "      .sort_values(ascending=False).head(10))",
        3
    ),
])

with open(NB_DIR / "05_anomaly_detection.ipynb", "w", encoding="utf-8") as f:
    json.dump(nb5, f, indent=1)

# ─────────────────────────────────────────────────────────────────────────────
# NB 6 — ML Models
# ─────────────────────────────────────────────────────────────────────────────
nb6 = nb([
    md(
        "# 06 — Machine Learning Demand Prediction\n"
        "Train all models, compare metrics, SHAP explainability, and live prediction.",
        0
    ),
    code(
        "import sys, pathlib\n"
        "sys.path.insert(0, str(pathlib.Path('..').resolve()))\n"
        "import pandas as pd\n\n"
        "metrics = pd.read_csv('../outputs/metrics/model_metrics.csv')\n"
        "test_m = metrics[metrics['split'] == 'test'].sort_values('R2', ascending=False)\n"
        "print('Model Comparison (Test Set):')\n"
        "test_m[['model_name','MAE','RMSE','MAPE','R2']]",
        1
    ),
    code(
        "import matplotlib.pyplot as plt\n"
        "from PIL import Image\n"
        "img = Image.open('../reports/figures/model_comparison.png')\n"
        "plt.figure(figsize=(14, 10))\n"
        "plt.imshow(img)\n"
        "plt.axis('off')\n"
        "plt.title('Model Performance Comparison')\n"
        "plt.show()",
        2
    ),
    code(
        "shap_imp = pd.read_csv('../outputs/metrics/shap_feature_importance.csv')\n"
        "print('Top 10 demand drivers (SHAP):')\n"
        "print(shap_imp.head(10).to_string(index=False))",
        3
    ),
    code(
        "img2 = Image.open('../reports/figures/shap_global_importance.png')\n"
        "plt.figure(figsize=(10, 7))\n"
        "plt.imshow(img2)\n"
        "plt.axis('off')\n"
        "plt.title('SHAP Global Feature Importance')\n"
        "plt.show()",
        4
    ),
    code(
        "img3 = Image.open('../reports/figures/shap_summary_plot.png')\n"
        "plt.figure(figsize=(11, 8))\n"
        "plt.imshow(img3)\n"
        "plt.axis('off')\n"
        "plt.title('SHAP Summary Plot')\n"
        "plt.show()",
        5
    ),
    code(
        "from src.ml.predict import predict_single\n\n"
        "result = predict_single(\n"
        "    route='Kurnool-Hyderabad',\n"
        "    date='2024-12-15',\n"
        "    bus_type='Volvo Ac',\n"
        "    distance_km=326.0,\n"
        "    capacity=49,\n"
        "    is_holiday=0,\n"
        "    bus_capacity=50,\n"
        ")\n"
        "print('Prediction Result:')\n"
        "for k, v in result.items():\n"
        "    print(f'  {k:25s}: {v}')",
        6
    ),
    code(
        "# Actual vs Predicted (test set)\n"
        "pred_df = pd.read_csv('../outputs/predictions/demand_predictions.csv')\n"
        "test_pred = pred_df[pred_df['split'] == 'test']\n\n"
        "plt.figure(figsize=(10, 6))\n"
        "plt.scatter(test_pred['actual_demand'], test_pred['predicted_demand'],\n"
        "            alpha=0.6, color='steelblue', s=35)\n"
        "mn, mx = test_pred['actual_demand'].min(), test_pred['actual_demand'].max()\n"
        "plt.plot([mn, mx], [mn, mx], 'r--', label='Perfect Fit')\n"
        "plt.xlabel('Actual Passengers')\n"
        "plt.ylabel('Predicted Passengers')\n"
        "plt.title('Actual vs Predicted Demand (Test Set)')\n"
        "plt.legend()\n"
        "plt.tight_layout()\n"
        "plt.savefig('../reports/figures/actual_vs_predicted.png', dpi=150)\n"
        "plt.show()",
        7
    ),
    md(
        "## SHAP Findings\n\n"
        "Top demand drivers identified by SHAP:\n"
        "1. **capacity** — Bus type capacity is the strongest predictor\n"
        "2. **rolling_mean_14** — 14-day historical average (strongest temporal predictor)\n"
        "3. **bus_type_encoded** — Service class significantly affects demand\n"
        "4. **week_of_year** — Seasonal patterns within the year\n"
        "5. **fare_per_passenger** — Price elasticity effect\n\n"
        "> Note: With only 1,000 records and 15 routes (~67 records/route),\n"
        "> tree models require hyperparameter tuning to generalise beyond training data.",
        8
    ),
])

with open(NB_DIR / "06_ml_models.ipynb", "w", encoding="utf-8") as f:
    json.dump(nb6, f, indent=1)

print("All 6 notebooks generated successfully in:", NB_DIR)
print("\nFiles created:")
for p in sorted(NB_DIR.glob("*.ipynb")):
    print(f"  {p.name}")
