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
from src.config import MODELS_DIR, RANDOM_SEED
from src.ml.preprocessing import prepare
from src.ml.evaluate import compute_metrics, save_metrics, build_comparison_table
from src.utils.logger import get_logger

warnings.filterwarnings("ignore")
logger = get_logger(__name__)


PARAM_GRIDS = {
    "XGBoost": {
        "model": XGBRegressor(random_state=RANDOM_SEED, verbosity=0, n_jobs=1),
        "params": {
            "n_estimators":     [100, 150, 200],
            "max_depth":        [4, 5, 6],
            "learning_rate":    [0.03, 0.05, 0.1],
            "subsample":        [0.8, 0.9, 1.0],
            "colsample_bytree": [0.7, 0.8, 1.0],
            "min_child_weight": [1, 3],
        }
    },
    "LightGBM": {
        "model": LGBMRegressor(random_state=RANDOM_SEED, verbose=-1, n_jobs=1),
        "params": {
            "n_estimators":    [100, 150, 200],
            "learning_rate":   [0.03, 0.05, 0.1],
            "num_leaves":      [31, 63],
            "max_depth":       [-1, 6],
            "subsample":       [0.8, 1.0],
            "colsample_bytree":[0.8, 1.0],
            "min_child_samples":[10, 20],
        }
    },
    "CatBoost": {
        "model": CatBoostRegressor(random_seed=RANDOM_SEED, verbose=0, thread_count=1),
        "params": {
            "iterations":   [100, 150, 200],
            "learning_rate":[0.03, 0.05, 0.1],
            "depth":        [4, 5, 6],
            "l2_leaf_reg":  [1, 3],
        }
    },
    "Random Forest": {
        "model": RandomForestRegressor(random_state=RANDOM_SEED, n_jobs=1),
        "params": {
            "n_estimators":    [100, 150],
            "max_depth":       [10, 15],
            "min_samples_leaf":[2, 5],
            "max_features":    ["sqrt", 0.5],
        }
    },
}


def tune_model(name: str, splits: dict, n_iter: int = 5) -> dict:
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
    tscv = TimeSeriesSplit(n_splits=3)

    search = RandomizedSearchCV(
        estimator=cfg["model"],
        param_distributions=cfg["params"],
        n_iter=n_iter,
        cv=tscv,
        scoring="neg_mean_absolute_error",
        refit=True,
        random_state=RANDOM_SEED,
        n_jobs=1,
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

    # Pick the best tuned model by CV MAE (lower = better).
    # Using CV score keeps the test set as a truly held-out, unbiased metric.
    best_name = min(results, key=lambda n: results[n]["cv_score"])
    best_info = results[best_name]
    logger.info("\n* Best tuned model: %s (CV MAE=%.4f)", best_name, best_info["cv_score"])

    # Save tuned model
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODELS_DIR / "tuned_model.pkl"
    joblib.dump(best_info["model"], model_path)

    # Overwrite best_model.pkl if tuned model beats previous best.
    # Comparison uses CV MAE (tuned) vs val MAE from stored metadata
    # to avoid using the test set as a selection criterion.
    prev_path = MODELS_DIR / "best_model.pkl"
    if prev_path.exists():
        prev_meta_path = MODELS_DIR / "model_metadata.json"
        if prev_meta_path.exists():
            import json as _json
            with open(prev_meta_path) as _f:
                prev_meta = _json.load(_f)
            # val_mae may not be in old metadata; fall back to accepting tuned
            prev_val_mae = prev_meta.get("metrics", {}).get("val_MAE", float("inf"))
        else:
            prev_val_mae = float("inf")

        # cv_score is already a positive MAE (lower = better)
        if best_info["cv_score"] < prev_val_mae:
            joblib.dump(best_info["model"], prev_path)
            logger.info("OK Tuned model BEATS previous best (CV MAE %.4f < prev val MAE %.4f). Updated best_model.pkl",
                        best_info["cv_score"], prev_val_mae)
        else:
            logger.info("Previous best model still wins (prev val MAE %.4f <= CV MAE %.4f). Keeping best_model.pkl.",
                        prev_val_mae, best_info["cv_score"])
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
