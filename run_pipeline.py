"""
run_pipeline.py — Master entry point for the Public Transport Demand Prediction project.

Usage:
    python run_pipeline.py [--steps all|etl|mine|train|tune|explain|predict]
    python run_pipeline.py --steps etl          # Only ETL
    python run_pipeline.py --steps etl,train    # ETL + Training
    python run_pipeline.py                       # Run all steps

Steps:
    etl      — Extract, Transform, Load all three datasets
    load_dw  — Load data into MySQL data warehouse
    mine     — K-Means clustering + Isolation Forest
    train    — Train all ML models and compare
    tune     — Hyperparameter tuning
    explain  — SHAP explainability
    predict  — Generate predictions (batch + single demo)
"""

import argparse
import sys
import time
from pathlib import Path

# Add src to path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.utils.logger import get_logger

logger = get_logger("run_pipeline")


VALID_STEPS = ["etl", "load_dw", "mine", "train", "tune", "explain", "predict"]


def run_etl():
    logger.info("\n" + "█"*60)
    logger.info(" STEP 1: ETL PIPELINE")
    logger.info("█"*60)
    from src.etl.pipeline import run_all
    return run_all()


def run_load_dw():
    logger.info("\n" + "█"*60)
    logger.info(" STEP 2: DATA WAREHOUSE LOAD")
    logger.info("█"*60)
    try:
        from src.warehouse.load import run
        run()
    except Exception as e:
        logger.warning("DW load skipped (MySQL may not be configured): %s", e)


def run_mining():
    logger.info("=" * 60)
    logger.info(" STEP 3: DATA MINING")
    logger.info("=" * 60)
    from src.mining.clustering import run as cluster_run
    from src.mining.anomaly_detection import run as anomaly_run
    cluster_df = cluster_run()
    anomaly_df = anomaly_run()
    return cluster_df, anomaly_df


def run_training():
    logger.info("\n" + "█"*60)
    logger.info(" STEP 4: ML TRAINING & EVALUATION")
    logger.info("█"*60)
    from src.ml.train import run
    return run()


def run_tuning():
    logger.info("\n" + "█"*60)
    logger.info(" STEP 5: HYPERPARAMETER TUNING")
    logger.info("█"*60)
    from src.ml.tune import run
    return run()


def run_explain():
    logger.info("\n" + "█"*60)
    logger.info(" STEP 6: SHAP EXPLAINABILITY")
    logger.info("█"*60)
    from src.ml.explain import run
    return run()


def run_predict():
    logger.info("\n" + "█"*60)
    logger.info(" STEP 7: PREDICTION PIPELINE")
    logger.info("█"*60)
    from src.ml.predict import run
    return run()


STEP_RUNNERS = {
    "etl":      run_etl,
    "load_dw":  run_load_dw,
    "mine":     run_mining,
    "train":    run_training,
    "tune":     run_tuning,
    "explain":  run_explain,
    "predict":  run_predict,
}


def main():
    parser = argparse.ArgumentParser(
        description="Public Transport Demand Prediction — Master Pipeline"
    )
    parser.add_argument(
        "--steps", default="all",
        help="Comma-separated steps: all | etl | load_dw | mine | train | tune | explain | predict"
    )
    args = parser.parse_args()

    if args.steps.strip().lower() == "all":
        steps = list(STEP_RUNNERS.keys())
    else:
        steps = [s.strip().lower() for s in args.steps.split(",")]
        invalid = [s for s in steps if s not in VALID_STEPS]
        if invalid:
            logger.error("Unknown steps: %s. Valid: %s", invalid, VALID_STEPS)
            sys.exit(1)

    logger.info("+" + "-"*54 + "+")
    logger.info("  PUBLIC TRANSPORT DEMAND PREDICTION PIPELINE")
    logger.info("  Steps: %s", ", ".join(steps))
    logger.info("+" + "-"*54 + "+")

    overall_start = time.time()
    results = {}

    for step in steps:
        t0 = time.time()
        try:
            result = STEP_RUNNERS[step]()
            elapsed = time.time() - t0
            results[step] = {"status": "OK", "elapsed_s": round(elapsed, 1)}
            logger.info("OK Step '%s' completed in %.1fs", step, elapsed)
        except Exception as e:
            elapsed = time.time() - t0
            results[step] = {"status": "FAILED", "error": str(e), "elapsed_s": round(elapsed, 1)}
            logger.error("FAILED Step '%s' in %.1fs: %s", step, elapsed, e)

    total = time.time() - overall_start
    logger.info("+" + "-"*54 + "+")
    logger.info("  PIPELINE COMPLETE -- %.1f seconds total", total)
    logger.info("+" + "-"*54 + "+")
    for step, info in results.items():
        status = info["status"]
        logger.info("  %-10s  %-6s  %.1fs", step, status, info["elapsed_s"])
    logger.info("+" + "-"*54 + "+")

    # Exit with error if any step failed
    if any(r["status"] == "FAILED" for r in results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
