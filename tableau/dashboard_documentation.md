# Tableau Dashboard Documentation
## Public Transport Demand Prediction — DMDW Project

---

## Connection Setup

**Data Source**: MySQL → `transport_dw` database

1. Open Tableau Desktop
2. Connect → MySQL
3. Server: `localhost` | Port: `3306` | Database: `transport_dw`
4. Username/Password from `.env`
5. Tables to use:
   - `fact_transport`
   - `dim_date`, `dim_route`, `dim_transport_mode`, `dim_location`
   - `fact_predictions`
   - `ml_model_metrics`
   - `mining_clusters`
   - `mining_anomalies`

**Also connect CSV files** from `outputs/` for supplemental Tableau views.

---

## Dashboard 1 — Executive Overview

**Purpose**: High-level KPI summary for transport authority leadership.

### KPI Cards (BANs)
| KPI | Calculation | Field |
|-----|-------------|-------|
| Total Routes | COUNT(DISTINCT route_name) | dim_route |
| Total Trips  | COUNT(fact_id) WHERE source_dataset='apsrtc' | fact_transport |
| Total Passengers | SUM(passenger_count) | fact_transport |
| Avg Demand/Trip | AVG(passenger_count) | fact_transport |
| Peak Demand | MAX(passenger_count) | fact_transport |
| Avg Occupancy | AVG(occupancy_rate) | fact_transport |

### Charts
1. **Line Chart**: Total passengers by month (dim_date.month_name on X, SUM(passenger_count) on Y)
2. **Horizontal Bar**: Top 10 routes by total passengers
3. **Stacked Bar**: Transport activity by mode (Bus / Flight / Railway)

### Filters
- Year (dim_date.year)
- Quarter (dim_date.quarter)
- Transport Mode (dim_transport_mode.mode_name)

---

## Dashboard 2 — Demand Analysis

**Purpose**: Deep-dive into APSRTC bus demand patterns.

### Charts
1. **Bar Chart**: Average passengers by day of week (dim_date.day_name)
2. **Heatmap**: Passengers heatmap — Month (rows) vs Day of Week (cols), colour = AVG(passengers)
3. **Line Chart**: Demand trend over time (monthly moving average)
4. **Box Plot / Bar**: Demand distribution by route
5. **Scatter**: Occupancy rate vs Passengers by route
6. **Bar Chart**: Revenue by route (top 15)

### Calculations (Tableau Calculated Fields)
```
Peak Hour Flag: IF [hour] >= 7 AND [hour] <= 10 OR [hour] >= 17 AND [hour] <= 21 THEN "Peak" ELSE "Off-Peak" END

Weekend Flag: IF [day_of_week] >= 5 THEN "Weekend" ELSE "Weekday" END

Demand Category: 
IF [passenger_count] < {FIXED : PERCENTILE([passenger_count], 0.33)} THEN "Low"
ELSEIF [passenger_count] > {FIXED : PERCENTILE([passenger_count], 0.66)} THEN "High"
ELSE "Medium" END
```

### Filters
- Date Range (dim_date.full_date)
- Route (dim_route.route_name)
- Bus Type (dim_transport_mode.sub_type)
- Month, Day of Week

---

## Dashboard 3 — Route Clustering (K-Means)

**Source**: `mining_clusters` table OR `outputs/predictions/route_clusters.csv`

**Purpose**: Show which routes are similar in demand characteristics.

### Charts
1. **Scatter Plot**: Avg Passengers (X) vs Avg Occupancy (Y), colour = cluster_name
2. **Bar Chart**: Average passengers per cluster (sorted)
3. **Table**: Route-to-cluster assignment with key metrics
4. **Treemap**: Cluster size (number of routes) with avg_revenue as size

### Colour coding
- Low Demand → Blue
- Medium Demand → Orange
- High Demand → Green
- Peak-Dependent → Purple

### Filters
- Cluster Name
- Avg Passengers range

---

## Dashboard 4 — Anomaly Detection

**Source**: `mining_anomalies` table OR `outputs/predictions/apsrtc_anomalies.csv`

**Purpose**: Flag unusual demand events for operational investigation.

### KPI Cards
- Total Records Analysed
- Anomalies Detected
- Anomaly Rate (%)
- Most Anomalous Route

### Charts
1. **Scatter**: Passengers vs Occupancy, colour = is_anomaly (Normal=blue, Anomaly=red)
2. **Bar Chart**: Anomaly count by route (top 10)
3. **Line Chart**: Anomalies over time (date on X, cumulative count on Y)
4. **Table**: Anomaly records with anomaly_score, route, date, passengers

### Calculated Field
```
Anomaly Label: IF [is_anomaly] = 1 THEN "Anomaly" ELSE "Normal" END
```

---

## Dashboard 5 — ML Model Performance

**Source**: `ml_model_metrics` table OR `outputs/metrics/model_metrics.csv`

**Purpose**: Academic model comparison and best-model selection.

### Charts
1. **Grouped Bar**: MAE by model (lower is better)
2. **Grouped Bar**: RMSE by model (lower is better)
3. **Grouped Bar**: MAPE (%) by model (lower is better)
4. **Grouped Bar**: R² by model (higher is better)
5. **Highlight Table**: All metrics in a single table with conditional colouring

### Best Model Highlight
- Add a reference line at best test R²
- Colour best-performing model distinctively

### Filters
- Split (validation / test)
- Model name

---

## Dashboard 6 — Demand Prediction

**Source**: `fact_predictions` table OR `outputs/predictions/demand_predictions.csv`

**Purpose**: Compare actual vs predicted demand; show forecast trends.

### KPI Cards
- Mean Absolute Error (from predictions)
- Mean Prediction
- Actual vs Predicted delta

### Charts
1. **Scatter**: Actual Demand (X) vs Predicted Demand (Y), reference line = perfect fit
2. **Dual-Axis Line**: Actual vs Predicted over time (date on X)
3. **Bar Chart**: Average prediction error by route (residual analysis)
4. **Pie/Donut**: Demand category distribution (Low / Medium / High)
5. **Table**: Top-10 worst predictions (largest |error|)

### Calculated Fields
```
Absolute Error: ABS([actual_demand] - [predicted_demand])

Prediction Accuracy: 1 - ABS([actual_demand] - [predicted_demand]) / [actual_demand]

Recommended Buses: INT(CEILING([predicted_demand] / [bus_capacity_used]))
```

### Filters
- Route
- Date range
- Bus type
- Demand category

---

## Dashboard Story / Presentation Order

For academic presentation, link dashboards in this order:

1. Executive Overview → Set the scene
2. Demand Analysis → Show patterns
3. Route Clustering → Group routes
4. Anomaly Detection → Flag issues
5. ML Model Performance → Justify model selection
6. Demand Prediction → Show ML results

---

## Tips for Tableau Public / Desktop

- Use **Extract** (not Live) connection for performance
- Create **Calculated Fields** for demand categories
- Use **Parameters** for bus_capacity (allows interactive what-if)
- Format numbers consistently (0 decimal for passengers, 2 decimal for rates)
- Use **Colour** consistently across dashboards (route colours match)
- Add **Dashboard titles** matching section names above
- Add **Data Source** annotation on each dashboard
