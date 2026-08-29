"""
ml/tune.py -- Hyperparameter tuning for the best-performing models.

Uses RandomizedSearchCV with cross-validation on the training set.
Saves tuned model as models/tuned_model.pkl
"""

import json
import warnings
from datetime import datetime
from pathlib import Path
import sys

import numpy as np
import joblib
from sklearn.model_selection import RandomizedSearchCV, TimeSeriesSplit
from xgboost import XGBRegressor
from lightgbm import LGBMRegressor
from catboost import CatBoostRegressor
from sklearn.ensemble import RandomForestRegressor

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import MODELS_DIR, RANDOM_SEED, METRICS_DIR
from src.ml.preprocessing import prepare
from src.ml.evaluate import compute_metrics, save_metrics, build_comparison_table
from src.utils.logger import get_logger

warnings.filterwarnings("ignore")
logger = get_logger(__name__)


PARAM_GRIDS = {
    "XGBoost": {
        "model": XGBRegressor(random_state=RANDOM_SEED, verbosity=0),
        "params": {
            "n_estimators":     [200, 300, 400, 500],
            "max_depth":        [4, 5, 6, 7, 8],
            "learning_rate":    [0.01, 0.03, 0.05, 0.1],
            "subsample":        [0.7, 0.8, 0.9, 1.0],
            "colsample_bytree": [0.6, 0.7, 0.8, 1.0],
            "min_child_weight": [1, 3, 5, 7],
            "gamma":            [0, 0.1, 0.2],
        }
    },
    "LightGBM": {
        "model": LGBMRegressor(random_state=RANDOM_SEED, verbose=-1),
        "params": {
            "n_estimators":    [200, 300, 400, 500],
            "learning_rate":   [0.01, 0.03, 0.05, 0.1],
            "num_leaves":      [31, 63, 127],
            "max_depth":       [-1, 6, 8, 10],
            "subsample":       [0.7, 0.8, 0.9],
            "colsample_bytree":[0.7, 0.8, 1.0],
            "min_child_samples":[5, 10, 20],
        }
    },
    "CatBoost": {
        "model": CatBoostRegressor(random_seed=RANDOM_SEED, verbose=0),
        "params": {
            "iterations":   [200, 300, 400],
            "learning_rate":[0.03, 0.05, 0.1],
            "depth":        [4, 5, 6, 7],
            "l2_leaf_reg":  [1, 3, 5, 7],
        }
    },
    "Random Forest": {
        "model": RandomForestRegressor(random_state=RANDOM_SEED, n_jobs=-1),
        "params": {
            "n_estimators":    [100, 200, 300],
            "max_depth":       [None, 10, 15, 20],
            "min_samples_leaf":[1, 2, 5],
            "max_features":    ["sqrt", "log2", 0.5],
        }
    },
}


def tune_model(name: str, splits: dict, n_iter: int = 25) -> dict:
    """Tune a single model using RandomizedSearchCV with TimeSeriesSplit."""
    X_train = splits["X_train"]
    y_train = splits["y_train"]
    X_val   = splits["X_val"]
    y_val   = splits["y_val"]
    X_test  = splits["X_test"]
    y_test  = splits["y_test"]

    if name not in PARAM_GRIDS:
        logger.warning("No param grid for '%s'. Skipping.", name)
        return {}

    logger.info("\n--- Tuning: %s (%d iterations) -----------------------", name, n_iter)
    cfg = PARAM_GRIDS[name]

    # TimeSeriesSplit for CV -- respects temporal ordering
    tscv = TimeSeriesSplit(n_splits=5)

    search = RandomizedSearchCV(
        estimator=cfg["model"],
        param_distributions=cfg["params"],
        n_iter=n_iter,
        cv=tscv,
        scoring="neg_mean_absolute_error",
        refit=True,
        random_state=RANDOM_SEED,
        n_jobs=-1,
        verbose=0,
    )

    # Combine train+val for tuning (still no test leakage)
    X_tv = np.vstack([X_train.values, X_val.values])
    y_tv = np.concatenate([y_train.values, y_val.values])

    search.fit(X_tv, y_tv)

    logger.info("Best params: %s", search.best_params_)
    logger.info("Best CV MAE: %.4f", -search.best_score_)

    best_model = search.best_estimator_

    # Evaluate tuned model on test set
    test_pred = np.clip(best_model.predict(X_test), 0, None)
    test_metrics = compute_metrics(y_test, test_pred, f"{name} (Tuned)", "test")

    return {
        "model": best_model,
        "best_params": search.best_params_,
        "cv_score": -search.best_score_,
        "test_metrics": test_metrics,
    }


def run(candidate_models: list = None) -> dict:
    """Tune specified models (defaults to XGBoost + LightGBM + CatBoost)."""
    logger.info("=== Hyperparameter Tuning START ===")

    if candidate_models is None:
        candidate_models = ["XGBoost", "LightGBM", "CatBoost"]

    splits = prepare()
    results = {}
    all_metrics = []

    for name in candidate_models:
        res = tune_model(name, splits)
        if res:
            results[name] = res
            all_metrics.append(res["test_metrics"])

    if not results:
        logger.warning("No tuning results. Exiting.")
        return {}

    # Pick the best tuned model
    best_name = max(results, key=lambda n: results[n]["test_metrics"]["R2"])
    best_info = results[best_name]
    logger.info("\n* Best tuned model: %s (Test R²=%.4f)", best_name, best_info["test_metrics"]["R2"])

    # Save tuned model
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODELS_DIR / "tuned_model.pkl"
    joblib.dump(best_info["model"], model_path)

    # Overwrite best_model.pkl with tuned version if it beats previous
    prev_path = MODELS_DIR / "best_model.pkl"
    if prev_path.exists():
        prev_model = joblib.load(prev_path)
        prev_pred = np.clip(prev_model.predict(splits["X_test"]), 0, None)
        from sklearn.metrics import r2_score
        prev_r2 = r2_score(splits["y_test"], prev_pred)
        if best_info["test_metrics"]["R2"] > prev_r2:
            joblib.dump(best_info["model"], prev_path)
            logger.info("OK Tuned model BEATS previous best. Updated best_model.pkl")
        else:
            logger.info("Previous best model still wins. Keeping best_model.pkl.")
    else:
        joblib.dump(best_info["model"], prev_path)

    # Save metadata
    meta = {
        "model_name":     f"{best_name} (Tuned)",
        "best_params":    best_info["best_params"],
        "cv_mae":         best_info["cv_score"],
        "features":       splits["feature_cols"],
        "training_date":  datetime.now().isoformat(),
        "metrics":        best_info["test_metrics"],
    }
    with open(MODELS_DIR / "tuned_model_metadata.json", "w") as f:
        json.dump(meta, f, indent=2)

    # Save metrics
    comparison = build_comparison_table(all_metrics)
    save_metrics(comparison, "tuned_model_metrics.csv")

    logger.info("Tuned model saved -> %s", model_path)
    logger.info("=== Hyperparameter Tuning END ===")
    return results


if __name__ == "__main__":
    run()
