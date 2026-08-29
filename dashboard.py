"""
dashboard.py — Streamlit Dashboard for APSRTC Public Transport Demand Prediction

Run with:
    streamlit run dashboard.py

Pages:
    1. Overview        — KPIs, quick stats
    2. Model Results   — Compare all 5 models, view prediction plots
    3. Predictions     — Explore all 1000 predictions, filter/sort
    4. Live Predict    — Input a trip, get instant prediction
    5. SHAP Analysis   — Feature importance & SHAP plots
    6. Data Explorer   — Raw and processed data tables
"""

import json
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from PIL import Image

warnings.filterwarnings("ignore")

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT          = Path(__file__).resolve().parent
METRICS_CSV   = ROOT / "outputs" / "metrics" / "model_metrics.csv"
SHAP_IMP_CSV  = ROOT / "outputs" / "metrics" / "shap_feature_importance.csv"
SHAP_VAL_CSV  = ROOT / "outputs" / "metrics" / "shap_values.csv"
PRED_CSV      = ROOT / "outputs" / "predictions" / "demand_predictions.csv"
FEAT_CSV      = ROOT / "data" / "processed" / "apsrtc_features.csv"
MODEL_META    = ROOT / "models" / "model_metadata.json"
BEST_MODEL    = ROOT / "models" / "best_model.pkl"
FIGURES       = ROOT / "reports" / "figures"

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="APSRTC Demand Prediction",
    page_icon="🚌",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Dark premium header */
.main-header {
    background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
    padding: 2rem 2.5rem;
    border-radius: 16px;
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
}
.main-header::before {
    content: '';
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: radial-gradient(circle at 30% 50%, rgba(120,80,255,0.15) 0%, transparent 60%);
}
.main-header h1 {
    color: #ffffff;
    font-size: 2rem;
    font-weight: 700;
    margin: 0;
    letter-spacing: -0.5px;
}
.main-header p {
    color: rgba(255,255,255,0.65);
    font-size: 0.95rem;
    margin: 0.4rem 0 0 0;
}

/* KPI Cards */
.kpi-card {
    background: linear-gradient(145deg, #1e1e2e, #2a2a3e);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px;
    padding: 1.4rem 1.6rem;
    text-align: center;
    transition: transform 0.2s, box-shadow 0.2s;
}
.kpi-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 12px 40px rgba(0,0,0,0.3);
}
.kpi-value {
    font-size: 2.4rem;
    font-weight: 700;
    color: #a78bfa;
    line-height: 1;
    margin-bottom: 0.3rem;
}
.kpi-label {
    font-size: 0.8rem;
    font-weight: 500;
    color: rgba(255,255,255,0.5);
    text-transform: uppercase;
    letter-spacing: 1px;
}
.kpi-sub {
    font-size: 0.75rem;
    color: rgba(255,255,255,0.35);
    margin-top: 0.2rem;
}

/* Section headers */
.section-title {
    font-size: 1.1rem;
    font-weight: 600;
    color: #e2e8f0;
    margin: 1.5rem 0 0.8rem 0;
    padding-bottom: 0.4rem;
    border-bottom: 2px solid rgba(167,139,250,0.3);
}

/* Demand badges */
.badge-high   { background:#ef4444; color:#fff; padding:2px 10px; border-radius:20px; font-size:0.78rem; font-weight:600; }
.badge-medium { background:#f59e0b; color:#fff; padding:2px 10px; border-radius:20px; font-size:0.78rem; font-weight:600; }
.badge-low    { background:#10b981; color:#fff; padding:2px 10px; border-radius:20px; font-size:0.78rem; font-weight:600; }

/* Prediction result box */
.pred-result {
    background: linear-gradient(135deg, #1a1a2e, #16213e);
    border: 1px solid rgba(167,139,250,0.3);
    border-radius: 16px;
    padding: 2rem;
    text-align: center;
}
.pred-number {
    font-size: 5rem;
    font-weight: 800;
    background: linear-gradient(135deg, #a78bfa, #60a5fa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    line-height: 1;
}
.pred-unit {
    font-size: 1rem;
    color: rgba(255,255,255,0.5);
    margin-top: 0.3rem;
}

/* Sidebar styling */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f0c29 0%, #1a1a2e 100%);
}
[data-testid="stSidebar"] * {
    color: rgba(255,255,255,0.85) !important;
}

/* Streamlit metric */
[data-testid="metric-container"] {
    background: linear-gradient(145deg, #1e1e2e, #2a2a3e);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px;
    padding: 1rem 1.2rem;
}

div[data-testid="stMetricValue"] {
    color: #a78bfa !important;
    font-weight: 700 !important;
}

/* Tab styling */
button[data-baseweb="tab"] {
    font-weight: 500 !important;
}

/* Expander */
.streamlit-expanderHeader {
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)


# ── Data Loaders ──────────────────────────────────────────────────────────────
@st.cache_data
def load_metrics():
    if not METRICS_CSV.exists():
        return pd.DataFrame()
    return pd.read_csv(METRICS_CSV)

@st.cache_data
def load_predictions():
    if not PRED_CSV.exists():
        return pd.DataFrame()
    df = pd.read_csv(PRED_CSV)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df

@st.cache_data
def load_shap_importance():
    if not SHAP_IMP_CSV.exists():
        return pd.DataFrame()
    return pd.read_csv(SHAP_IMP_CSV)

@st.cache_data
def load_features():
    if not FEAT_CSV.exists():
        return pd.DataFrame()
    df = pd.read_csv(FEAT_CSV)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df

@st.cache_data
def load_model_meta():
    if not MODEL_META.exists():
        return {}
    with open(MODEL_META) as f:
        return json.load(f)

@st.cache_resource
def load_best_model():
    if not BEST_MODEL.exists():
        return None
    return joblib.load(BEST_MODEL)


def load_img(path: Path):
    if path.exists():
        return Image.open(path)
    return None


# ── Sidebar Navigation ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🚌 APSRTC Dashboard")
    st.markdown("---")
    page = st.radio(
        "Navigate",
        ["🏠 Overview", "📊 Model Results", "🔍 Predictions Explorer",
         "⚡ Live Predict", "🧠 SHAP Analysis", "📁 Data Explorer"],
        label_visibility="collapsed"
    )
    st.markdown("---")
    meta = load_model_meta()
    if meta:
        st.markdown("**Best Model**")
        st.markdown(f"`{meta.get('model_name', 'CatBoost')}`")
        m = meta.get("metrics", {})
        st.markdown(f"Test MAE: **{m.get('test_MAE', '—')}**")
        st.markdown(f"Test R²: **{m.get('test_R2', '—')}**")
        st.markdown(f"Features: **{meta.get('n_features', 25)}**")
    st.markdown("---")
    st.caption("Public Transport Demand Prediction\nAPSRTC · 2024 Dataset · 1,000 trips")


# ── Load all data ─────────────────────────────────────────────────────────────
metrics_df    = load_metrics()
pred_df       = load_predictions()
shap_imp      = load_shap_importance()
feat_df       = load_features()
meta          = load_model_meta()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1: OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
if page == "🏠 Overview":
    st.markdown("""
    <div class="main-header">
        <h1>🚌 Public Transport Demand Prediction</h1>
        <p>APSRTC · Andhra Pradesh State Road Transport Corporation · ML-Powered Passenger Forecasting</p>
    </div>
    """, unsafe_allow_html=True)

    # ── KPIs ──────────────────────────────────────────────────────────────────
    if not pred_df.empty:
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.markdown(f"""<div class="kpi-card">
                <div class="kpi-value">{len(pred_df):,}</div>
                <div class="kpi-label">Total Trips</div>
                <div class="kpi-sub">Jan–Dec 2024</div>
            </div>""", unsafe_allow_html=True)
        with col2:
            n_routes = pred_df["route"].nunique() if "route" in pred_df.columns else 15
            st.markdown(f"""<div class="kpi-card">
                <div class="kpi-value">{n_routes}</div>
                <div class="kpi-label">Routes</div>
                <div class="kpi-sub">Andhra Pradesh</div>
            </div>""", unsafe_allow_html=True)
        with col3:
            avg_pred = int(pred_df["predicted_demand"].mean()) if "predicted_demand" in pred_df.columns else 37
            st.markdown(f"""<div class="kpi-card">
                <div class="kpi-value">{avg_pred}</div>
                <div class="kpi-label">Avg Predicted</div>
                <div class="kpi-sub">passengers/trip</div>
            </div>""", unsafe_allow_html=True)
        with col4:
            best_mae = meta.get("metrics", {}).get("test_MAE", 7.98)
            st.markdown(f"""<div class="kpi-card">
                <div class="kpi-value">{best_mae}</div>
                <div class="kpi-label">Best MAE</div>
                <div class="kpi-sub">passengers off</div>
            </div>""", unsafe_allow_html=True)
        with col5:
            best_r2 = meta.get("metrics", {}).get("test_R2", 0.24)
            st.markdown(f"""<div class="kpi-card">
                <div class="kpi-value">{best_r2:.2f}</div>
                <div class="kpi-label">Best R²</div>
                <div class="kpi-sub">CatBoost test</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Charts row ────────────────────────────────────────────────────────────
    col_a, col_b = st.columns([3, 2])

    with col_a:
        st.markdown('<div class="section-title">📈 Predicted Demand by Route</div>', unsafe_allow_html=True)
        if not pred_df.empty and "route" in pred_df.columns:
            route_avg = (pred_df.groupby("route")["predicted_demand"]
                         .mean().sort_values(ascending=True).reset_index())
            fig = px.bar(
                route_avg, x="predicted_demand", y="route",
                orientation="h",
                color="predicted_demand",
                color_continuous_scale="Viridis",
                labels={"predicted_demand": "Avg Predicted Passengers", "route": "Route"},
            )
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#cbd5e1", size=11),
                margin=dict(l=10, r=10, t=10, b=10),
                coloraxis_showscale=False,
                height=400,
            )
            fig.update_xaxes(showgrid=True, gridcolor="rgba(255,255,255,0.06)")
            fig.update_yaxes(showgrid=False)
            st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.markdown('<div class="section-title">🎯 Demand Category Split</div>', unsafe_allow_html=True)
        if not pred_df.empty and "demand_category" in pred_df.columns:
            cat_counts = pred_df["demand_category"].value_counts().reset_index()
            cat_counts.columns = ["Category", "Count"]
            color_map = {"High": "#ef4444", "Medium": "#f59e0b", "Low": "#10b981"}
            fig2 = px.pie(
                cat_counts, values="Count", names="Category",
                color="Category", color_discrete_map=color_map,
                hole=0.55,
            )
            fig2.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#cbd5e1"),
                legend=dict(orientation="h", yanchor="bottom", y=-0.2),
                margin=dict(l=10, r=10, t=10, b=30),
                height=320,
            )
            fig2.update_traces(textposition="outside", textinfo="percent+label")
            st.plotly_chart(fig2, use_container_width=True)

    # ── Demand over time ──────────────────────────────────────────────────────
    st.markdown('<div class="section-title">📅 Passenger Demand Over Time (Actual vs Predicted)</div>', unsafe_allow_html=True)
    if not pred_df.empty and "date" in pred_df.columns:
        time_df = (pred_df.groupby("date")[["actual_demand", "predicted_demand"]]
                   .mean().reset_index())
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(
            x=time_df["date"], y=time_df["actual_demand"],
            name="Actual", line=dict(color="#60a5fa", width=2),
            fill="tozeroy", fillcolor="rgba(96,165,250,0.08)"
        ))
        fig3.add_trace(go.Scatter(
            x=time_df["date"], y=time_df["predicted_demand"],
            name="Predicted", line=dict(color="#a78bfa", width=2, dash="dash"),
        ))
        fig3.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#cbd5e1"),
            margin=dict(l=10, r=10, t=10, b=10),
            legend=dict(bgcolor="rgba(0,0,0,0)"),
            height=280,
            xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
        )
        st.plotly_chart(fig3, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2: MODEL RESULTS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📊 Model Results":
    st.markdown("""
    <div class="main-header">
        <h1>📊 Model Performance Comparison</h1>
        <p>5 models trained and evaluated · CatBoost · XGBoost · LightGBM · Random Forest · Ridge</p>
    </div>
    """, unsafe_allow_html=True)

    if not metrics_df.empty:
        test_df = metrics_df[metrics_df["split"] == "test"].copy()
        val_df  = metrics_df[metrics_df["split"] == "validation"].copy()

        # ── Summary table ─────────────────────────────────────────────────────
        st.markdown('<div class="section-title">Test Set Performance</div>', unsafe_allow_html=True)
        display = test_df[["model_name", "MAE", "RMSE", "MAPE", "R2"]].copy()
        display = display.sort_values("MAE").reset_index(drop=True)
        display.columns = ["Model", "MAE ↓", "RMSE ↓", "MAPE% ↓", "R² ↑"]
        st.dataframe(
            display.style
                .highlight_min(subset=["MAE ↓", "RMSE ↓", "MAPE% ↓"], color="#1a3a2a")
                .highlight_max(subset=["R² ↑"], color="#1a2a3a")
                .format({"MAE ↓": "{:.3f}", "RMSE ↓": "{:.3f}", "MAPE% ↓": "{:.2f}", "R² ↑": "{:.4f}"}),
            use_container_width=True,
            height=220
        )

        # ── Side-by-side bar charts ───────────────────────────────────────────
        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<div class="section-title">MAE by Model (lower = better)</div>', unsafe_allow_html=True)
            fig = px.bar(
                test_df.sort_values("MAE"), x="model_name", y="MAE",
                color="MAE", color_continuous_scale="RdYlGn_r",
                text_auto=".2f",
            )
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#cbd5e1"), margin=dict(l=5,r=5,t=5,b=5),
                coloraxis_showscale=False, height=300,
                xaxis=dict(title=""), yaxis=dict(title="MAE", showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown('<div class="section-title">R² by Model (higher = better)</div>', unsafe_allow_html=True)
            fig2 = px.bar(
                test_df.sort_values("R2", ascending=False), x="model_name", y="R2",
                color="R2", color_continuous_scale="Viridis",
                text_auto=".3f",
            )
            fig2.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#cbd5e1"), margin=dict(l=5,r=5,t=5,b=5),
                coloraxis_showscale=False, height=300,
                xaxis=dict(title=""), yaxis=dict(title="R²", showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
            )
            st.plotly_chart(fig2, use_container_width=True)

        # ── Radar chart ───────────────────────────────────────────────────────
        st.markdown('<div class="section-title">Model Radar Comparison</div>', unsafe_allow_html=True)
        fig_radar = go.Figure()
        categories = ["MAE (inv)", "RMSE (inv)", "R2"]
        colors = ["#a78bfa", "#60a5fa", "#34d399", "#f59e0b", "#f87171"]
        for i, (_, row) in enumerate(test_df.iterrows()):
            # Invert MAE/RMSE so higher = better on radar
            mae_inv  = 1 / (1 + row["MAE"])
            rmse_inv = 1 / (1 + row["RMSE"])
            r2_norm  = max(0, row["R2"])
            fig_radar.add_trace(go.Scatterpolar(
                r=[mae_inv, rmse_inv, r2_norm, mae_inv],
                theta=categories + [categories[0]],
                name=row["model_name"],
                line=dict(color=colors[i % len(colors)], width=2),
                fill="toself", fillcolor=colors[i % len(colors)].replace(")", ",0.07)").replace("rgba", "rgba"),
                opacity=0.85
            ))
        fig_radar.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            polar=dict(bgcolor="rgba(0,0,0,0)", radialaxis=dict(visible=True, color="rgba(255,255,255,0.2)")),
            font=dict(color="#cbd5e1"),
            legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h"),
            height=380, margin=dict(l=10, r=10, t=10, b=10)
        )
        st.plotly_chart(fig_radar, use_container_width=True)

        # ── Prediction scatter plots ───────────────────────────────────────────
        st.markdown('<div class="section-title">Actual vs Predicted Scatter Plots</div>', unsafe_allow_html=True)
        plot_files = list(FIGURES.glob("predictions_*.png"))
        if plot_files:
            cols = st.columns(min(3, len(plot_files)))
            for i, pf in enumerate(sorted(plot_files)):
                with cols[i % 3]:
                    img = load_img(pf)
                    if img:
                        name = pf.stem.replace("predictions_", "").replace("_", " ").title()
                        st.image(img, caption=name, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3: PREDICTIONS EXPLORER
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔍 Predictions Explorer":
    st.markdown("""
    <div class="main-header">
        <h1>🔍 Predictions Explorer</h1>
        <p>Browse, filter and analyse all 1,000 trip predictions from the CatBoost model</p>
    </div>
    """, unsafe_allow_html=True)

    if pred_df.empty:
        st.warning("No predictions found. Run `python run_pipeline.py --steps predict` first.")
    else:
        # ── Filters ───────────────────────────────────────────────────────────
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            routes = ["All"] + sorted(pred_df["route"].dropna().unique().tolist())
            sel_route = st.selectbox("Route", routes)
        with col2:
            cats = ["All"] + sorted(pred_df["demand_category"].dropna().unique().tolist())
            sel_cat = st.selectbox("Demand Category", cats)
        with col3:
            bus_types = ["All"] + sorted(pred_df["bus_type"].dropna().unique().tolist()) if "bus_type" in pred_df.columns else ["All"]
            sel_bt = st.selectbox("Bus Type", bus_types)
        with col4:
            splits = ["All"] + sorted(pred_df["split"].dropna().unique().tolist()) if "split" in pred_df.columns else ["All"]
            sel_split = st.selectbox("Data Split", splits)

        filt = pred_df.copy()
        if sel_route != "All": filt = filt[filt["route"] == sel_route]
        if sel_cat   != "All": filt = filt[filt["demand_category"] == sel_cat]
        if sel_bt    != "All" and "bus_type" in filt.columns: filt = filt[filt["bus_type"] == sel_bt]
        if sel_split != "All" and "split" in filt.columns: filt = filt[filt["split"] == sel_split]

        # ── KPI strip ─────────────────────────────────────────────────────────
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Trips Shown", f"{len(filt):,}")
        c2.metric("Avg Predicted", f"{filt['predicted_demand'].mean():.1f}" if len(filt) else "—")
        c3.metric("Avg Actual",    f"{filt['actual_demand'].mean():.1f}" if len(filt) and "actual_demand" in filt.columns else "—")
        mae_filt = (filt["actual_demand"] - filt["predicted_demand"]).abs().mean() if len(filt) and "actual_demand" in filt.columns else None
        c4.metric("MAE (filtered)", f"{mae_filt:.2f}" if mae_filt else "—")

        st.markdown("<br>", unsafe_allow_html=True)

        col_l, col_r = st.columns(2)

        with col_l:
            st.markdown('<div class="section-title">Error Distribution</div>', unsafe_allow_html=True)
            if "actual_demand" in filt.columns and len(filt) > 0:
                errors = filt["actual_demand"] - filt["predicted_demand"]
                fig_err = px.histogram(
                    errors, nbins=30,
                    labels={"value": "Prediction Error (Actual − Predicted)"},
                    color_discrete_sequence=["#a78bfa"]
                )
                fig_err.add_vline(x=0, line_dash="dash", line_color="#ef4444")
                fig_err.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#cbd5e1"), margin=dict(l=5,r=5,t=5,b=5),
                    height=280, showlegend=False,
                    xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
                    yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
                )
                st.plotly_chart(fig_err, use_container_width=True)

        with col_r:
            st.markdown('<div class="section-title">Predicted vs Actual Scatter</div>', unsafe_allow_html=True)
            if "actual_demand" in filt.columns and len(filt) > 0:
                fig_sc = px.scatter(
                    filt, x="actual_demand", y="predicted_demand",
                    color="demand_category",
                    color_discrete_map={"High": "#ef4444", "Medium": "#f59e0b", "Low": "#10b981"},
                    hover_data=["route"] if "route" in filt.columns else [],
                    opacity=0.65,
                )
                mn = min(filt["actual_demand"].min(), filt["predicted_demand"].min())
                mx = max(filt["actual_demand"].max(), filt["predicted_demand"].max())
                fig_sc.add_trace(go.Scatter(x=[mn, mx], y=[mn, mx], mode="lines",
                    line=dict(color="#ef4444", dash="dash", width=1.5), name="Perfect Fit"))
                fig_sc.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#cbd5e1"), margin=dict(l=5,r=5,t=5,b=5), height=280,
                    legend=dict(bgcolor="rgba(0,0,0,0)"),
                    xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
                    yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
                )
                st.plotly_chart(fig_sc, use_container_width=True)

        # ── Data table ────────────────────────────────────────────────────────
        st.markdown('<div class="section-title">Prediction Records</div>', unsafe_allow_html=True)
        show_cols = [c for c in ["date", "route", "bus_type", "actual_demand",
                                  "predicted_demand", "demand_category",
                                  "prediction_error", "recommended_buses"] if c in filt.columns]
        st.dataframe(
            filt[show_cols].sort_values("date", ascending=False).head(200),
            use_container_width=True, height=350
        )
        st.caption(f"Showing up to 200 of {len(filt)} filtered rows")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4: LIVE PREDICT
# ══════════════════════════════════════════════════════════════════════════════
elif page == "⚡ Live Predict":
    st.markdown("""
    <div class="main-header">
        <h1>⚡ Live Demand Prediction</h1>
        <p>Enter trip details and get an instant passenger demand forecast from the CatBoost model</p>
    </div>
    """, unsafe_allow_html=True)

    col_form, col_result = st.columns([1, 1])

    with col_form:
        st.markdown('<div class="section-title">Trip Details</div>', unsafe_allow_html=True)

        routes_list = sorted(feat_df["route"].unique().tolist()) if not feat_df.empty else [
            "Kurnool-Hyderabad", "Vijayawada-Hyderabad", "Tirupati-Chennai",
            "Visakhapatnam-Hyderabad", "Guntur-Hyderabad"
        ]
        bus_types_list = sorted(feat_df["bus_type"].unique().tolist()) if not feat_df.empty else [
            "Volvo Ac", "Sleeper", "Express", "Garuda Plus", "Garuda"
        ]

        route        = st.selectbox("Route", routes_list, key="lp_route")
        date_input   = st.date_input("Date", value=pd.Timestamp("2024-12-25"), key="lp_date")
        bus_type     = st.selectbox("Bus Type", bus_types_list, key="lp_bt")

        c1, c2 = st.columns(2)
        with c1:
            distance_km = st.number_input("Distance (km)", min_value=10.0, max_value=1000.0, value=326.0, step=10.0)
            capacity    = st.number_input("Bus Capacity (seats)", min_value=20, max_value=80, value=49)
        with c2:
            fare        = st.number_input("Fare per Passenger (₹)", min_value=10.0, max_value=2000.0, value=908.0, step=10.0)
            is_holiday  = st.selectbox("Is Holiday?", [("No", 0), ("Yes", 1)], format_func=lambda x: x[0])
            bus_cap     = st.number_input("Bus Capacity for # Buses", min_value=20, max_value=80, value=50)

        predict_btn = st.button("🚀 Predict Demand", use_container_width=True, type="primary")

    with col_result:
        st.markdown('<div class="section-title">Prediction Result</div>', unsafe_allow_html=True)

        if predict_btn:
            with st.spinner("Running prediction..."):
                try:
                    import sys
                    sys.path.insert(0, str(ROOT))
                    from src.ml.predict import predict_single

                    result = predict_single(
                        route=route,
                        date=str(date_input),
                        bus_type=bus_type,
                        distance_km=float(distance_km),
                        capacity=int(capacity),
                        fare_per_passenger=float(fare),
                        is_holiday=int(is_holiday[1]),
                        bus_capacity=int(bus_cap),
                    )

                    pred  = result["predicted_demand"]
                    cat   = result["demand_category"]
                    buses = result["recommended_buses"]
                    cat_color = {"High": "#ef4444", "Medium": "#f59e0b", "Low": "#10b981"}.get(cat, "#a78bfa")

                    st.markdown(f"""
                    <div class="pred-result">
                        <div class="pred-number">{pred}</div>
                        <div class="pred-unit">predicted passengers</div>
                        <br>
                        <span style="background:{cat_color};color:#fff;padding:6px 20px;
                              border-radius:30px;font-weight:700;font-size:1rem;">{cat} Demand</span>
                        <br><br>
                        <div style="color:rgba(255,255,255,0.6);font-size:0.9rem;">
                            Recommended buses: <strong style="color:#a78bfa">{buses}</strong>
                            &nbsp;|&nbsp; Model: <strong style="color:#a78bfa">{result['model_name']}</strong>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Gauge chart
                    st.markdown("<br>", unsafe_allow_html=True)
                    fig_gauge = go.Figure(go.Indicator(
                        mode="gauge+number",
                        value=pred,
                        title={"text": "Occupancy Estimate", "font": {"color": "#cbd5e1", "size": 14}},
                        gauge={
                            "axis": {"range": [0, int(capacity)], "tickcolor": "#cbd5e1"},
                            "bar": {"color": cat_color},
                            "bgcolor": "rgba(0,0,0,0)",
                            "steps": [
                                {"range": [0, capacity*0.33], "color": "rgba(16,185,129,0.15)"},
                                {"range": [capacity*0.33, capacity*0.66], "color": "rgba(245,158,11,0.15)"},
                                {"range": [capacity*0.66, capacity], "color": "rgba(239,68,68,0.15)"},
                            ],
                        },
                        number={"suffix": " pax", "font": {"color": "#a78bfa", "size": 32}},
                    ))
                    fig_gauge.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#cbd5e1"),
                        height=240, margin=dict(l=30, r=30, t=30, b=10)
                    )
                    st.plotly_chart(fig_gauge, use_container_width=True)

                except Exception as e:
                    st.error(f"Prediction failed: {e}")
                    st.info("Make sure you've run `python run_pipeline.py` first.")
        else:
            st.markdown("""
            <div style="text-align:center;padding:3rem 1rem;color:rgba(255,255,255,0.3);">
                <div style="font-size:4rem;">🚌</div>
                <div style="font-size:1rem;margin-top:1rem;">Fill in trip details and click<br><strong>Predict Demand</strong></div>
            </div>
            """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 5: SHAP ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🧠 SHAP Analysis":
    st.markdown("""
    <div class="main-header">
        <h1>🧠 SHAP Explainability</h1>
        <p>Understand what drives passenger demand · Feature importance ranked by mean |SHAP| value</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Interactive SHAP bar chart ─────────────────────────────────────────────
    if not shap_imp.empty:
        st.markdown('<div class="section-title">Feature Importance (Mean |SHAP|)</div>', unsafe_allow_html=True)
        shap_top = shap_imp.head(20).sort_values("mean_abs_shap", ascending=True)
        fig_shap = px.bar(
            shap_top, x="mean_abs_shap", y="feature",
            orientation="h",
            color="mean_abs_shap",
            color_continuous_scale="Purples",
            labels={"mean_abs_shap": "Mean |SHAP Value|", "feature": "Feature"},
            text_auto=".3f",
        )
        fig_shap.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#cbd5e1"), margin=dict(l=10, r=10, t=10, b=10),
            coloraxis_showscale=False, height=520,
            xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
        )
        st.plotly_chart(fig_shap, use_container_width=True)

    # ── SHAP plots from files ─────────────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        img = load_img(FIGURES / "shap_global_importance.png")
        if img:
            st.markdown('<div class="section-title">Global SHAP Bar Chart</div>', unsafe_allow_html=True)
            st.image(img, use_container_width=True)

    with col2:
        img2 = load_img(FIGURES / "shap_summary_plot.png")
        if img2:
            st.markdown('<div class="section-title">SHAP Beeswarm Summary</div>', unsafe_allow_html=True)
            st.image(img2, use_container_width=True)

    img3 = load_img(FIGURES / "shap_waterfall_single.png")
    if img3:
        st.markdown('<div class="section-title">Single Prediction Waterfall (Record #0)</div>', unsafe_allow_html=True)
        st.image(img3, use_column_width=True)

    # ── Key insights ─────────────────────────────────────────────────────────
    st.markdown('<div class="section-title">Key Insights</div>', unsafe_allow_html=True)
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.info("**🚌 Capacity is #1**\nBus size (capacity) is the single strongest predictor — larger buses fill more seats.")
    with col_b:
        st.info("**📍 Route history matters**\n`route_hist_mean` is #2 — each route has a consistent baseline demand level.")
    with col_c:
        st.info("**🚍 Bus type signal**\n`bustype_hist_mean` is #3 — premium buses (Volvo AC) attract more passengers.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 6: DATA EXPLORER
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📁 Data Explorer":
    st.markdown("""
    <div class="main-header">
        <h1>📁 Data Explorer</h1>
        <p>Browse the processed APSRTC dataset and engineered features</p>
    </div>
    """, unsafe_allow_html=True)

    if feat_df.empty:
        st.warning("Feature data not found. Run ETL first: `python run_pipeline.py --steps etl`")
    else:
        st.markdown(f"**Dataset:** {len(feat_df):,} rows × {len(feat_df.columns)} columns")

        tab1, tab2, tab3 = st.tabs(["📋 Data Table", "📊 Distributions", "🗺️ Route Stats"])

        with tab1:
            show_cols = [c for c in ["date", "route", "bus_type", "depot", "capacity",
                                      "passengers", "distance_km", "fare_per_passenger",
                                      "route_hist_mean", "bustype_hist_mean", "is_weekend", "is_holiday"]
                         if c in feat_df.columns]
            st.dataframe(feat_df[show_cols].sort_values("date", ascending=False).head(500),
                         use_container_width=True, height=400)

        with tab2:
            col_sel = st.selectbox("Select column to plot",
                                   [c for c in ["passengers", "capacity", "distance_km",
                                                 "fare_per_passenger", "route_hist_mean"] if c in feat_df.columns])
            fig_dist = px.histogram(feat_df, x=col_sel, nbins=40,
                                    color_discrete_sequence=["#a78bfa"])
            fig_dist.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#cbd5e1"), margin=dict(l=5,r=5,t=5,b=5), height=320,
                xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
                yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
            )
            st.plotly_chart(fig_dist, use_container_width=True)

            # Box plot by bus type
            if "bus_type" in feat_df.columns and "passengers" in feat_df.columns:
                st.markdown('<div class="section-title">Passengers by Bus Type</div>', unsafe_allow_html=True)
                fig_box = px.box(feat_df, x="bus_type", y="passengers",
                                 color="bus_type", color_discrete_sequence=px.colors.qualitative.Vivid)
                fig_box.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#cbd5e1"), margin=dict(l=5,r=5,t=5,b=5), height=320,
                    showlegend=False,
                    xaxis=dict(showgrid=False),
                    yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
                )
                st.plotly_chart(fig_box, use_container_width=True)

        with tab3:
            if "route" in feat_df.columns and "passengers" in feat_df.columns:
                route_stats = feat_df.groupby("route")["passengers"].agg(
                    ["mean", "min", "max", "std", "count"]
                ).round(2).reset_index()
                route_stats.columns = ["Route", "Avg Passengers", "Min", "Max", "Std Dev", "Trips"]
                route_stats = route_stats.sort_values("Avg Passengers", ascending=False)

                fig_rs = px.bar(
                    route_stats, x="Avg Passengers", y="Route", orientation="h",
                    error_x="Std Dev",
                    color="Avg Passengers", color_continuous_scale="Viridis",
                    text_auto=".1f",
                )
                fig_rs.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#cbd5e1"), margin=dict(l=10,r=10,t=10,b=10),
                    coloraxis_showscale=False, height=480,
                    xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
                )
                st.plotly_chart(fig_rs, use_container_width=True)
                st.dataframe(route_stats, use_container_width=True)
