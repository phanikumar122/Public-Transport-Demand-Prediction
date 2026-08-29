"""
ml/evaluate.py — Model evaluation utilities.

Computes: MAE, RMSE, MAPE, R²
Produces: comparison table, bar charts
"""

from pathlib import Path
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import FIGURES_DIR, METRICS_DIR
from src.utils.logger import get_logger

logger = get_logger(__name__)
plt.style.use("seaborn-v0_8-whitegrid")


def compute_metrics(y_true, y_pred, model_name: str, split: str = "test") -> dict:
    """Compute MAE, RMSE, MAPE, R² for a single model."""
    y_true = np.array(y_true, dtype=float)
    y_pred = np.array(y_pred, dtype=float)

    mae  = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2   = r2_score(y_true, y_pred)

    # MAPE — guard against zero targets
    mask = y_true != 0
    mape = np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100 if mask.any() else np.nan

    metrics = {
        "model_name": model_name,
        "split": split,
        "MAE":  round(mae, 4),
        "RMSE": round(rmse, 4),
        "MAPE": round(mape, 4),
        "R2":   round(r2, 6),
    }
    logger.info(
        "%-20s [%s]  MAE=%.2f  RMSE=%.2f  MAPE=%.2f%%  R2=%.4f",
        model_name, split, mae, rmse, mape, r2
    )
    return metrics


def build_comparison_table(metrics_list: list) -> pd.DataFrame:
    """Create comparison DataFrame from list of metric dicts."""
    df = pd.DataFrame(metrics_list)
    df = df.sort_values("R2", ascending=False).reset_index(drop=True)
    logger.info("\nModel Comparison Table:\n%s", df.to_string(index=False))
    return df


def save_metrics(df: pd.DataFrame, fname: str = "model_metrics.csv"):
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    path = METRICS_DIR / fname
    df.to_csv(path, index=False)
    logger.info("Metrics saved -> %s", path)
    return path


def plot_comparison(df: pd.DataFrame):
    """Plot MAE, RMSE, MAPE, R² side-by-side bar charts."""
    metrics_to_plot = ["MAE", "RMSE", "MAPE", "R2"]
    # Filter to test split
    plot_df = df[df["split"] == "test"].copy() if "split" in df.columns else df.copy()

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    colors = sns.color_palette("husl", len(plot_df))

    for ax, metric in zip(axes.flatten(), metrics_to_plot):
        ascending = (metric != "R2")
        sorted_df = plot_df.sort_values(metric, ascending=ascending)
        bars = ax.barh(sorted_df["model_name"], sorted_df[metric], color=colors)
        ax.set_title(f"{metric} by Model", fontsize=13, fontweight="bold")
        ax.set_xlabel(metric)
        for bar, val in zip(bars, sorted_df[metric]):
            ax.text(bar.get_width() * 1.01, bar.get_y() + bar.get_height() / 2,
                    f"{val:.3f}", va="center", fontsize=9)

    plt.suptitle("Model Performance Comparison", fontsize=16, fontweight="bold", y=1.01)
    plt.tight_layout()
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    out = FIGURES_DIR / "model_comparison.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info("Model comparison chart -> %s", out)


def plot_predictions(y_true, y_pred, model_name: str):
    """Actual vs predicted scatter + residual plot."""
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Actual vs Predicted
    axes[0].scatter(y_true, y_pred, alpha=0.4, color="steelblue", s=25)
    mn, mx = min(y_true.min(), y_pred.min()), max(y_true.max(), y_pred.max())
    axes[0].plot([mn, mx], [mn, mx], "r--", linewidth=2, label="Perfect Fit")
    axes[0].set_xlabel("Actual Passengers")
    axes[0].set_ylabel("Predicted Passengers")
    axes[0].set_title(f"{model_name} - Actual vs Predicted", fontsize=13, fontweight="bold")
    axes[0].legend()

    # Residuals
    residuals = y_true - y_pred
    axes[1].scatter(y_pred, residuals, alpha=0.4, color="darkorange", s=25)
    axes[1].axhline(0, color="red", linestyle="--", linewidth=2)
    axes[1].set_xlabel("Predicted Passengers")
    axes[1].set_ylabel("Residual")
    axes[1].set_title(f"{model_name} - Residual Plot", fontsize=13, fontweight="bold")

    plt.tight_layout()
    safe_name = model_name.lower().replace(" ", "_")
    out = FIGURES_DIR / f"predictions_{safe_name}.png"
    plt.savefig(out, dpi=150)
    plt.close()
    logger.info("Prediction plot -> %s", out)
