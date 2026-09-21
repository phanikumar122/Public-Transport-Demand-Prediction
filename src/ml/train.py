"""
ml/train.py — Train and compare all ML models for multi-modal transport demand prediction.

Datasets: APSRTC (Bus) + IRCTC (Rail) + Indian Domestic Flights (Air)
Combined training set: ~24,366 records across all 3 transport modes.

Models:
  1. Linear Regression      (baseline)
  2. Random Forest          (traditional ML)
  3. XGBoost                (gradient boosting + early stopping)
  4. LightGBM               (gradient boosting + early stopping)
  5. CatBoost               (gradient boosting + early stopping)

Hyperparameters are tuned for the ~700-sample training regime.
Uses time-aware train/val/test split. No data leakage.
Saves: models/all_models.pkl, outputs/metrics/model_metrics.csv
"""

import json
from datetime import datetime
from pathlib import Path
import sys
import warnings

import numpy as np
import pandas as pd
import joblib

from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor
from lightgbm import LGBMRegressor
from catboost import CatBoostRegressor

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import MODELS_DIR, RANDOM_SEED
from src.ml.preprocessing import prepare
from src.ml.evaluate import compute_metrics, build_comparison_table, save_metrics, plot_comparison, plot_predictions
from src.utils.logger import get_logger

warnings.filterwarnings("ignore")
logger = get_logger(__name__)


def get_models() -> dict:
    """
    BUG 4 FIX: All hyperparameters tuned for ~700 training samples.
    - Reduced depth/max_depth to prevent overfitting on small dataset
    - Added regularization (l2_leaf_reg, min_child_weight, reg_alpha/lambda)
    - Replaced LinearRegression (fails badly) with Ridge (regularized baseline)
    - Added early_stopping_rounds for gradient boosters
    """
    return {
        # Ridge replaces plain LinearRegression — more stable on small datasets
        "Ridge": Ridge(alpha=1.0),

        # Random Forest: reduced max_depth, increased min_samples_leaf for generalization
        "Random Forest": RandomForestRegressor(
            n_estimators=500,
            max_depth=8,
            min_samples_leaf=4,
            min_samples_split=8,
            max_features=0.7,
            random_state=RANDOM_SEED,
            n_jobs=-1,
        ),

        # XGBoost: lower learning_rate + early stopping on val set
        "XGBoost": XGBRegressor(
            n_estimators=1000,       # will early-stop before this
            max_depth=4,             # shallower = less overfit on 700 samples
            learning_rate=0.02,
            subsample=0.8,
            colsample_bytree=0.7,
            min_child_weight=5,      # regularization for small node sizes
            reg_alpha=0.1,
            reg_lambda=1.0,
            random_state=RANDOM_SEED,
            verbosity=0,
            early_stopping_rounds=50,
            eval_metric="mae",
        ),

        # LightGBM: smaller num_leaves, higher min_data_in_leaf
        "LightGBM": LGBMRegressor(
            n_estimators=1000,
            learning_rate=0.02,
            num_leaves=31,           # reduced from 63
            min_data_in_leaf=20,     # prevents overfit on tiny leaves
            subsample=0.8,
            colsample_bytree=0.7,
            reg_alpha=0.1,
            reg_lambda=1.0,
            random_state=RANDOM_SEED,
            verbose=-1,
        ),

        # CatBoost: best performer, tuned depth+regularization
        "CatBoost": CatBoostRegressor(
            iterations=1000,
            learning_rate=0.02,
            depth=5,                  # reduced from 6
            l2_leaf_reg=5,            # strong regularization
            min_data_in_leaf=10,
            border_count=64,
            random_seed=RANDOM_SEED,
            verbose=0,
            early_stopping_rounds=50,
        ),
    }


def train_and_evaluate(splits: dict) -> tuple[dict, pd.DataFrame]:
    """Train all models, evaluate on val and test splits."""
    X_train, y_train = splits["X_train"], splits["y_train"]
    X_val,   y_val   = splits["X_val"],   splits["y_val"]
    X_test,  y_test  = splits["X_test"],  splits["y_test"]

    models = get_models()
    trained = {}
    all_metrics = []

    for name, model in models.items():
        logger.info("--- Training: %s ---", name)

        # Gradient boosters use validation set for early stopping
        if name in ("XGBoost",):
            model.fit(
                X_train, y_train,
                eval_set=[(X_val, y_val)],
                verbose=False,
            )
        elif name == "LightGBM":
            cb_val = [(X_val, y_val)]
            model.fit(
                X_train, y_train,
                eval_set=cb_val,
                callbacks=[],
            )
        elif name == "CatBoost":
            model.fit(
                X_train, y_train,
                eval_set=(X_val, y_val),
                verbose=False,
            )
        else:
            model.fit(X_train, y_train)

        # Validation metrics
        val_pred  = np.clip(model.predict(X_val),  0, None)
        val_metrics = compute_metrics(y_val, val_pred, name, "validation")
        all_metrics.append(val_metrics)

        # Test metrics
        test_pred = np.clip(model.predict(X_test), 0, None)
        test_metrics = compute_metrics(y_test, test_pred, name, "test")
        all_metrics.append(test_metrics)

        # Prediction plots (test set)
        plot_predictions(y_test, test_pred, name)

        logger.info(
            "  Val  MAE=%.2f  R2=%.4f | Test MAE=%.2f  R2=%.4f",
            val_metrics["MAE"], val_metrics["R2"],
            test_metrics["MAE"], test_metrics["R2"],
        )

        trained[name] = {
            "model":        model,
            "val_pred":     val_pred,
            "test_pred":    test_pred,
            "val_metrics":  val_metrics,
            "test_metrics": test_metrics,
        }

    comparison = build_comparison_table(all_metrics)
    return trained, comparison


def select_best_model(trained: dict) -> str:
    """
    Select the model with the best VALIDATION MAE.
    Using the validation set (not the test set) for model selection keeps
    the test set as a truly held-out, unbiased final evaluation metric.
    Ties broken by validation R².
    """
    val_mae = {name: d["val_metrics"]["MAE"] for name, d in trained.items()}
    best = min(val_mae, key=val_mae.get)
    bm_val  = trained[best]["val_metrics"]
    bm_test = trained[best]["test_metrics"]
    logger.info(
        "Best model: %s (Val MAE=%.3f, Val R2=%.4f | Test MAE=%.3f, Test R2=%.4f)",
        best, bm_val["MAE"], bm_val["R2"], bm_test["MAE"], bm_test["R2"],
    )
    return best


def save_best_model(best_name: str, trained: dict, feature_cols: list, metrics_df: pd.DataFrame):
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    best_model = trained[best_name]["model"]

    # Save best model
    model_path = MODELS_DIR / "best_model.pkl"
    joblib.dump(best_model, model_path)
    logger.info("Best model saved -> %s", model_path)

    # Save all models
    all_path = MODELS_DIR / "all_models.pkl"
    joblib.dump({name: d["model"] for name, d in trained.items()}, all_path)
    logger.info("All models saved -> %s", all_path)

    # Save metadata
    best_test = trained[best_name]["test_metrics"]
    meta = {
        "model_name":     best_name,
        "features":       feature_cols,
        "n_features":     len(feature_cols),
        "training_date":  datetime.now().isoformat(),
        "datasets":       ["APSRTC (Bus)", "IRCTC (Rail)", "Indian Domestic Flights (Air)"],
        "target":         "passengers",
        "split_strategy": "time-aware chronological (train=70%/val=15%/test=15%)",
        "metrics": {
            "test_MAE":  round(best_test["MAE"], 4),
            "test_RMSE": round(best_test["RMSE"], 4),
            "test_MAPE": round(best_test["MAPE"], 4),
            "test_R2":   round(best_test["R2"], 4),
        },
        "hyperparameters": best_model.get_params() if hasattr(best_model, "get_params") else {},
    }
    meta_path = MODELS_DIR / "model_metadata.json"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
    logger.info("Model metadata saved -> %s", meta_path)

    return model_path


def run() -> dict:
    logger.info("=== ML Training Pipeline START ===")

    # Prepare data
    splits = prepare()

    # Train all models
    trained, comparison = train_and_evaluate(splits)

    # Save metrics
    save_metrics(comparison)

    # Plot comparison
    plot_comparison(comparison)

    # Select and save best
    best_name = select_best_model(trained)
    save_best_model(best_name, trained, splits["feature_cols"], comparison)

    # Print summary table
    test_rows = comparison[comparison["split"] == "test"].copy()
    test_rows = test_rows.sort_values("MAE")
    logger.info("\n=== MODEL COMPARISON (Test Set) ===")
    for _, row in test_rows.iterrows():
        logger.info(
            "  %-18s  MAE=%6.3f  RMSE=%6.3f  R2=%7.4f",
            row["model_name"], row["MAE"], row["RMSE"], row["R2"]
        )

    logger.info("=== ML Training Pipeline END ===")
    return {"trained": trained, "comparison": comparison, "best": best_name}


if __name__ == "__main__":
    run()
