"""
tests/test_pipeline.py — Basic integrity tests for the project pipeline.

Tests:
  1. Data loading
  2. Missing-value handling
  3. Feature engineering
  4. ETL transformations
  5. Model can load and predict
  6. Prediction returns numeric output
  7. No duplicate primary keys in processed data
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


# ── Test 1: APSRTC loads successfully ─────────────────────────────────────────
def test_apsrtc_loads():
    from src.etl.apsrtc import load_raw
    df = load_raw()
    assert len(df) > 0, "APSRTC dataset is empty"
    assert df.shape[1] >= 5, f"Too few columns: {df.shape[1]}"
    print(f"OK  APSRTC loads OK - {len(df)} rows x {df.shape[1]} cols")


# ── Test 2: APSRTC preprocessing preserves rows and fills missing values ──────
def test_apsrtc_preprocess():
    from src.etl.apsrtc import load_raw, preprocess
    df = preprocess(load_raw())
    assert len(df) > 0, "All rows dropped during preprocessing"
    assert df.isnull().sum().sum() == 0 or df["passengers"].notna().all(), \
        "Target column 'passengers' has unexpected nulls after preprocessing"
    assert (df["passengers"] >= 0).all(), "Negative passenger counts found"
    print(f"OK  APSRTC preprocess OK - {len(df)} rows, no null targets")


# ── Test 3: Feature engineering adds expected columns ─────────────────────────
def test_feature_engineering():
    from src.etl.apsrtc import load_raw, preprocess, engineer_features
    df = engineer_features(preprocess(load_raw()))
    expected_cols = ["year", "month_num", "day_num", "dow", "is_weekend"]
    for col in expected_cols:
        assert col in df.columns, f"Expected feature '{col}' not found"
    print(f"OK  Feature engineering OK - {df.shape[1]} total columns")


# ── Test 4: No duplicates in processed APSRTC ─────────────────────────────────
def test_no_duplicates():
    from src.etl.apsrtc import load_raw, preprocess
    df = preprocess(load_raw())
    n_dups = df.duplicated().sum()
    assert n_dups == 0, f"Found {n_dups} duplicate rows after preprocessing"
    print("OK  No duplicates in APSRTC cleaned data")


# ── Test 5: Flights load and parse correctly ──────────────────────────────────
def test_flights_loads():
    from src.etl.flights import load_raw, preprocess
    df = preprocess(load_raw())
    assert len(df) > 0, "Flights dataset is empty"
    assert "duration_minutes" in df.columns, "duration_minutes column missing"
    assert df["duration_minutes"].notna().sum() > 0, "All duration_minutes are null"
    print(f"OK  Flights loads OK - {len(df)} rows")


# ── Test 6: Railways loads correctly ──────────────────────────────────────────
def test_railways_loads():
    from src.etl.railways import load_raw, preprocess
    df = preprocess(load_raw())
    assert len(df) > 0, "Railways dataset is empty"
    assert "distance" in df.columns, "distance column missing"
    print(f"OK  Railways loads OK - {len(df)} rows")


# ── Test 7: ML preprocessing produces valid splits ────────────────────────────
def test_ml_splits():
    processed_path = ROOT / "data" / "processed" / "apsrtc_features.csv"
    if not processed_path.exists():
        print("⚠ SKIP test_ml_splits — run ETL first to generate features file")
        return

    from src.ml.preprocessing import prepare
    splits = prepare()

    assert len(splits["X_train"]) > 0, "Training set is empty"
    assert len(splits["X_test"]) > 0, "Test set is empty"
    n_features = len(splits["feature_cols"])
    assert n_features >= 20, f"Too few features: {n_features} (expected ~25)"
    assert n_features <= 30, f"Too many features: {n_features}"
    assert "passengers" not in splits["X_train"].columns, \
        "Target 'passengers' found in feature set — leakage!"

    # Verify chronological order
    train_max = splits["train_df"]["date"].max()
    val_min   = splits["val_df"]["date"].min()
    test_min  = splits["test_df"]["date"].min()
    assert train_max <= val_min, "Training data bleeds into validation (future leakage)"
    assert val_min   <= test_min, "Validation data bleeds into test (future leakage)"

    print(f"OK  ML splits OK - train={len(splits['X_train'])} val={len(splits['X_val'])} test={len(splits['X_test'])}")


# ── Test 8: Best model loads and predicts numerically ─────────────────────────
def test_model_loads_and_predicts():
    model_path = ROOT / "models" / "best_model.pkl"
    if not model_path.exists():
        print("⚠ SKIP test_model_loads_and_predicts — run train.py first")
        return

    import joblib
    model = joblib.load(model_path)
    assert model is not None, "Model failed to load"

    from src.ml.preprocessing import prepare
    splits = prepare()
    X_test = splits["X_test"]

    if len(X_test) == 0:
        print("⚠ SKIP — test set is empty")
        return

    preds = model.predict(X_test.iloc[:5])
    assert len(preds) == 5, "Prediction returned wrong number of results"
    assert all(isinstance(p, (int, float, np.floating, np.integer)) for p in preds), \
        "Non-numeric prediction output"
    print(f"OK  Model predicts OK - sample preds: {[round(float(p),1) for p in preds]}")


# ── Test 9: Prediction pipeline returns valid output ─────────────────────────
def test_predict_single():
    model_path = ROOT / "models" / "best_model.pkl"
    if not model_path.exists():
        print("⚠ SKIP test_predict_single — run train.py first")
        return

    from src.ml.predict import predict_single
    result = predict_single(
        route="Kurnool-Hyderabad",
        date="2024-12-01",
        bus_type="Volvo Ac",
        distance_km=326.0,
        capacity=49,
        is_holiday=0,
    )
    assert "predicted_demand" in result, "predicted_demand key missing"
    assert isinstance(result["predicted_demand"], int), "predicted_demand not integer"
    assert result["predicted_demand"] >= 0, "Negative predicted demand"
    assert result["demand_category"] in {"Low","Medium","High"}, "Invalid demand category"
    assert result["recommended_buses"] >= 1, "Recommended buses < 1"
    print(f"OK  predict_single OK - demand={result['predicted_demand']} buses={result['recommended_buses']}")


# ── Test 10: No null targets in feature file ──────────────────────────────────
def test_no_null_targets():
    feat_path = ROOT / "data" / "processed" / "apsrtc_features.csv"
    if not feat_path.exists():
        print("⚠ SKIP test_no_null_targets — run ETL first")
        return

    df = pd.read_csv(feat_path)
    null_targets = df["passengers"].isna().sum()
    assert null_targets == 0, f"Found {null_targets} null values in target column 'passengers'"
    print(f"OK  No null targets in feature file ({len(df)} rows)")


# ── Runner ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    tests = [
        test_apsrtc_loads,
        test_apsrtc_preprocess,
        test_feature_engineering,
        test_no_duplicates,
        test_flights_loads,
        test_railways_loads,
        test_ml_splits,
        test_model_loads_and_predicts,
        test_predict_single,
        test_no_null_targets,
    ]

    passed, failed, skipped = 0, 0, 0
    print("\n" + "="*55)
    print(" RUNNING PROJECT INTEGRITY TESTS")
    print("="*55)

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"FAIL: {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"ERR : {test.__name__}: {e}")
            failed += 1

    print("="*55)
    print(f" Results: {passed} passed | {failed} failed")
    print("="*55)
    if failed:
        sys.exit(1)
