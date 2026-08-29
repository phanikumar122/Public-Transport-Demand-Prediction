"""
ml/explain.py — SHAP-based Explainable AI for the best model.

Produces:
  1. Global feature importance (bar chart)
  2. SHAP summary plot (beeswarm)
  3. Feature impact explanation
  4. Individual prediction explanation (waterfall)
  5. Saved SHAP values CSV for Tableau

Answers: Which factors drive public transport demand?
"""

import warnings
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import shap
import joblib

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import MODELS_DIR, FIGURES_DIR, METRICS_DIR, RANDOM_SEED
from src.ml.preprocessing import prepare
from src.utils.logger import get_logger

warnings.filterwarnings("ignore")
logger = get_logger(__name__)
plt.style.use("seaborn-v0_8-whitegrid")


def load_best_model():
    path = MODELS_DIR / "best_model.pkl"
    if not path.exists():
        raise FileNotFoundError(f"Best model not found at {path}. Run train.py first.")
    model = joblib.load(path)
    logger.info("Loaded best model: %s", type(model).__name__)
    return model


def compute_shap(model, X_sample: pd.DataFrame) -> tuple:
    """Compute SHAP values using appropriate explainer."""
    model_name = type(model).__name__

    try:
        if "CatBoost" in model_name:
            explainer = shap.TreeExplainer(model)
        elif "LGBM" in model_name or "LightGBM" in model_name:
            explainer = shap.TreeExplainer(model)
        elif "XGB" in model_name:
            explainer = shap.TreeExplainer(model)
        elif "Forest" in model_name:
            explainer = shap.TreeExplainer(model)
        else:
            # Linear model fallback
            explainer = shap.LinearExplainer(model, X_sample)

        shap_values = explainer.shap_values(X_sample)
        logger.info("SHAP values computed. Shape: %s", np.array(shap_values).shape)
        return explainer, shap_values
    except Exception as e:
        logger.error("SHAP computation failed: %s", e)
        raise


def plot_global_importance(shap_values, X_sample: pd.DataFrame):
    """Bar chart of mean |SHAP| per feature."""
    mean_abs = np.abs(shap_values).mean(axis=0)
    importance_df = pd.DataFrame({
        "feature": X_sample.columns.tolist(),
        "mean_abs_shap": mean_abs
    }).sort_values("mean_abs_shap", ascending=False)

    fig, ax = plt.subplots(figsize=(10, max(6, len(importance_df) * 0.35)))
    bars = ax.barh(importance_df["feature"][:20][::-1],
                   importance_df["mean_abs_shap"][:20][::-1],
                   color="steelblue", alpha=0.85)
    ax.set_xlabel("Mean |SHAP Value|", fontsize=12)
    ax.set_title("Global Feature Importance (SHAP)", fontsize=14, fontweight="bold")
    ax.tick_params(axis="y", labelsize=9)
    plt.tight_layout()
    out = FIGURES_DIR / "shap_global_importance.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info("Global SHAP importance -> %s", out)

    # Save importance CSV
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    importance_df.to_csv(METRICS_DIR / "shap_feature_importance.csv", index=False)

    return importance_df


def plot_summary(shap_values, X_sample: pd.DataFrame):
    """SHAP beeswarm summary plot."""
    fig, ax = plt.subplots(figsize=(11, 8))
    shap.summary_plot(shap_values, X_sample, show=False, max_display=20,
                      plot_type="dot")
    plt.title("SHAP Feature Impact Summary", fontsize=14, fontweight="bold")
    plt.tight_layout()
    out = FIGURES_DIR / "shap_summary_plot.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info("SHAP summary plot -> %s", out)


def plot_waterfall_single(explainer, shap_values, X_sample: pd.DataFrame, idx: int = 0):
    """Waterfall plot for a single prediction."""
    try:
        expected_value = explainer.expected_value
        if isinstance(expected_value, (list, np.ndarray)):
            expected_value = expected_value[0]

        shap_exp = shap.Explanation(
            values=shap_values[idx],
            base_values=expected_value,
            data=X_sample.iloc[idx].values,
            feature_names=X_sample.columns.tolist(),
        )
        fig, ax = plt.subplots(figsize=(12, 7))
        shap.plots.waterfall(shap_exp, show=False)
        plt.title(f"Single Prediction Explanation (record #{idx})",
                  fontsize=13, fontweight="bold")
        plt.tight_layout()
        out = FIGURES_DIR / "shap_waterfall_single.png"
        plt.savefig(out, dpi=150, bbox_inches="tight")
        plt.close()
        logger.info("Waterfall plot -> %s", out)
    except Exception as e:
        logger.warning("Waterfall plot failed: %s", e)


def print_feature_impact(importance_df: pd.DataFrame, top_n: int = 10):
    """Log human-readable SHAP feature impact summary."""
    logger.info("\n=== TOP %d FACTORS DRIVING DEMAND ===", top_n)
    for i, row in importance_df.head(top_n).iterrows():
        logger.info("  %-30s  mean|SHAP|=%.4f", row["feature"], row["mean_abs_shap"])
    logger.info("========================================")


def run() -> pd.DataFrame:
    logger.info("=== SHAP Explainability START ===")
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    model = load_best_model()
    splits = prepare()

    # Use test set for explanation (unbiased)
    X_test = splits["X_test"]

    # Sample for efficiency (SHAP can be slow on large sets)
    sample_size = min(200, len(X_test))
    X_sample = X_test.sample(n=sample_size, random_state=RANDOM_SEED).reset_index(drop=True)
    logger.info("Using %d test samples for SHAP analysis", sample_size)

    explainer, shap_values = compute_shap(model, X_sample)
    importance_df = plot_global_importance(shap_values, X_sample)
    plot_summary(shap_values, X_sample)
    plot_waterfall_single(explainer, shap_values, X_sample, idx=0)
    print_feature_impact(importance_df)

    # Save SHAP values as CSV for Tableau
    shap_df = pd.DataFrame(shap_values, columns=X_sample.columns)
    shap_df.to_csv(METRICS_DIR / "shap_values.csv", index=False)
    logger.info("SHAP values CSV -> %s", METRICS_DIR / "shap_values.csv")

    logger.info("=== SHAP Explainability END ===")
    return importance_df


if __name__ == "__main__":
    run()
