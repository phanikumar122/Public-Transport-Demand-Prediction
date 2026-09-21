# Transport Pulse AI — Multi-Modal Public Transport Demand Forecasting & Fleet Optimization

A full-stack, enterprise-grade AI research and operational telemetry portal for multi-modal public transit demand forecasting, real-time fleet allocation, unsupervised route clustering, anomaly radar detection, and SHAP explainability across **APSRTC Bus Corridors**, **Indian Railways**, and **Domestic Aviation Networks**.

---

## 🏛️ Professional & Institutional UI Refactoring

The user interface has been restructured from casual "vibe-coded" aesthetics to an **academic, institutional, and research-grade engineering layout**:

1. **Information Density & Compact Spacing**:
   - Eliminated excessive whitespace, dead margins, and oversized gaps (`p-12` replaced with compact, structured `p-4` grid cards).
   - Sidebar tightened to a clean 240px (`w-60`) width with high-contrast active state indicators and low-profile telemetry badges.
   - Header condensed to a clean 56px institutional breadcrumb bar with live dataset versioning.

2. **Clean Typography & Contrast**:
   - **Display Headings**: `Space Grotesk` (tight tracking `-0.025em`) for structured academic authority.
   - **Body & Data Grid**: `Outfit` with high contrast Slate 900 text on clean neutral `#f8fafc` / `#ffffff` cards.
   - **Tabular Figures & Metrics**: `JetBrains Mono` with tabular numerals (`tnum`) for exact visual alignment of passenger counts, fares, and statistical scores.

3. **Restrained, Professional Palette Integration**:
   - User palette (`crimson-carrot`, `tropical-mint`, `neon-ice`, `periwinkle`, `bright-lemon`) applied as **purposeful analytical indicators** rather than overwhelming saturated backgrounds:
     - Crimson Carrot (`#fb5012`): Bus network actuals & primary action triggers.
     - Tropical Mint (`#03fcba`): Indian Railways actuals & positive SHAP drivers.
     - Neon Ice (`#01fdf6` / `#00d4cf`): Domestic aviation trajectory series.
     - Neutral Periwinkle & Slate: Structured 1px card borders and subtle dividers.

---

## 📊 Modules & Academic Workspaces

1. **Executive Telemetry & Multi-Modal Overview (`OverviewDashboard.tsx`)**
   - 4 compact KPI stat cards with clear baseline context.
   - 2-column continuous time-series trajectories (2019–2025) and modal mix distribution.
   - Dense corridor benchmark matrix table.

2. **Operational Dispatch Simulator (`PredictionSimulator.tsx`)**
   - Clean parameter panel with zero wasted space.
   - Real-time optimal vehicle units, passenger load factors, and local SHAP factor waterfall charts.

3. **Model Benchmark Lab (`ModelPerformance.tsx`)**
   - Empirical comparison matrix across CatBoost, LightGBM, XGBoost, Random Forest, and Ridge.
   - Out-of-time test holdout metrics ($R^2 = 72.42\%$, $\text{MAE} = 25.34$, $\text{RMSE} = 39.34$).

4. **Unsupervised Corridor Clustering (`ClusterAnalysis.tsx`)**
   - K-Means 2D behavioral scatter space and cohort policy breakdown.

5. **Statistical Anomaly Radar (`AnomalyDetection.tsx`)**
   - Isolation Forest dispersion plane with real-time contamination threshold slider.

6. **SHAP Feature Interpretability Studio (`ExplainabilityStudio.tsx`)**
   - TreeExplainer relative importance bar chart and directional local force indicators.

7. **Operational Predictions Catalog (`BatchExplorer.tsx`)**
   - Searchable, multi-modal filtered predictions table with CSV export.

---

## 🚀 Running the App

```bash
# Backend (FastAPI on Port 8000)
python run_api.py

# Frontend (Vite on Port 5173)
cd frontend
npm run dev
```
