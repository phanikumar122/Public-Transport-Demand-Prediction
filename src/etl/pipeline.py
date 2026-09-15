"""
etl/pipeline.py -- Master ETL orchestrator.

Usage:
    python -m etl.pipeline              # Run all three pipelines
    python run_pipeline.py              # From project root
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.utils.logger import get_logger
from src.etl import apsrtc, railways, flights

logger = get_logger(__name__)


def run_all():
    logger.info("========================================================")
    logger.info(" PUBLIC TRANSPORT DEMAND PREDICTION -- ETL PIPELINE")
    logger.info("========================================================")

    results = {}

    # -- 1. APSRTC -------------------------------------------------------------
    logger.info("\n[1/3] Running APSRTC pipeline...")
    try:
        df_apsrtc = apsrtc.run()
        results["apsrtc"] = {"status": "OK", "rows": len(df_apsrtc), "cols": df_apsrtc.shape[1]}
        logger.info("OK APSRTC: %d rows x %d cols", *df_apsrtc.shape)
    except Exception as e:
        logger.error("FAIL APSRTC failed: %s", e)
        results["apsrtc"] = {"status": "FAILED", "error": str(e)}

    # -- 2. Railways -----------------------------------------------------------
    logger.info("\n[2/3] Running Railways pipeline...")
    try:
        df_rail = railways.run()
        results["railways"] = {"status": "OK", "rows": len(df_rail), "cols": df_rail.shape[1]}
        logger.info("OK Railways: %d rows x %d cols", *df_rail.shape)
    except Exception as e:
        logger.error("FAIL Railways failed: %s", e)
        results["railways"] = {"status": "FAILED", "error": str(e)}

    # -- 3. Flights ------------------------------------------------------------
    logger.info("\n[3/3] Running Flights pipeline...")
    try:
        df_flights = flights.run()
        results["flights"] = {"status": "OK", "rows": len(df_flights), "cols": df_flights.shape[1]}
        logger.info("OK Flights: %d rows x %d cols", *df_flights.shape)
    except Exception as e:
        logger.error("FAIL Flights failed: %s", e)
        results["flights"] = {"status": "FAILED", "error": str(e)}

    # -- Summary ---------------------------------------------------------------
    logger.info("\n========================================================")
    logger.info(" ETL SUMMARY")
    logger.info("========================================================")
    for ds, info in results.items():
        if info["status"] == "OK":
            logger.info("  %-10s -> OK  (%d rows x %d cols)", ds, info["rows"], info["cols"])
        else:
            logger.error("  %-10s -> FAILED: %s", ds, info.get("error",""))

    return results


if __name__ == "__main__":
    run_all()
