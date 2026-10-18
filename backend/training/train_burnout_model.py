"""Train Random Forest burnout classifier with baselines, CV, and light tuning."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import GridSearchCV, StratifiedKFold, cross_val_score, train_test_split

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.ml.preprocessing import validate_frame, impute_numeric  # noqa: E402
from app.ml.feature_engineering import assemble_matrix, FEATURE_ORDER  # noqa: E402
from app.ml.burnout_model import baselines, build_random_forest  # noqa: E402
from app.ml.semantic_model import SemanticEncoder  # noqa: E402
from app.config import MODEL_VERSION, DATASET_VERSION  # noqa: E402

DS = ROOT / "datasets" / "burnout_training.csv"
OUT = ROOT / "models"
OUT.mkdir(exist_ok=True)


def _metrics(y_true, y_pred, labels):
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision_macro": float(precision_score(y_true, y_pred, average="macro", zero_division=0)),
        "recall_macro": float(recall_score(y_true, y_pred, average="macro", zero_division=0)),
        "f1_macro": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "recall_high": float(recall_score(y_true, y_pred, labels=["HIGH"], average="macro", zero_division=0)),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=labels).tolist(),
        "classification_report": classification_report(y_true, y_pred, labels=labels, output_dict=True, zero_division=0),
    }


def main():
    df = validate_frame(pd.read_csv(DS))
    df, medians = impute_numeric(df)
    labels = ["LOW", "MODERATE", "HIGH"]
    y = df["burnout_label"].astype(str)

    enc_path = OUT / "semantic_encoder.joblib"
    if enc_path.exists():
        enc = joblib.load(enc_path)
    else:
        enc = SemanticEncoder().fit(df["communication_text"].fillna("").tolist())
        joblib.dump(enc, enc_path)
    sem = enc.derived_features(df["communication_text"].fillna("").tolist())
    X = assemble_matrix(df, sem)
    # employee-aware split: unique employee_id
    emp = df["employee_id"].values
    uniq = np.unique(emp)
    # stratify by majority label per employee (1 row each here)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    comparison = {}
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    for name, model in baselines().items():
        model.fit(Xtr, ytr)
        pred = model.predict(Xte)
        m = _metrics(yte, pred, labels)
        cv_f1 = cross_val_score(model, Xtr, ytr, cv=cv, scoring="f1_macro")
        m["cv_f1_mean"] = float(cv_f1.mean())
        m["cv_f1_std"] = float(cv_f1.std())
        comparison[name] = m
        print(name, m["accuracy"], m["f1_macro"], "cv", m["cv_f1_mean"])

    grid = GridSearchCV(
        build_random_forest(),
        {
            "n_estimators": [120, 180],
            "max_depth": [8, 10],
            "min_samples_leaf": [2, 4],
        },
        cv=3,
        scoring="f1_macro",
        n_jobs=-1,
    )
    grid.fit(Xtr, ytr)
    best = grid.best_estimator_
    pred = best.predict(Xte)
    rf_metrics = _metrics(yte, pred, labels)
    rf_metrics["best_params"] = grid.best_params_
    rf_metrics["cv_f1_mean"] = float(grid.best_score_)
    comparison["Random Forest (tuned)"] = rf_metrics

    importances = [
        {"name": n, "importance": float(i)}
        for n, i in sorted(zip(FEATURE_ORDER, best.feature_importances_), key=lambda x: -x[1])
    ]
    dist = y.value_counts().to_dict()
    meta = {
        "disclaimer": "Prototype / Demonstration Dataset. Trained on synthetic_v1 correlated workplace features with controlled label noise. Not real employee data. Not a medical model.",
        "model_version": MODEL_VERSION,
        "dataset_version": DATASET_VERSION,
        "feature_version": "fusion_v1",
        "training_date": datetime.now(timezone.utc).isoformat(),
        "dataset_size": int(len(df)),
        "n_train": int(len(Xtr)),
        "n_test": int(len(Xte)),
        "class_distribution": {str(k): int(v) for k, v in dist.items()},
        "score_mapping": "p_LOW*20 + p_MODERATE*60 + p_HIGH*90",
        "semantic_backend": getattr(enc, "backend", "tfidf_svd"),
        "comparison": comparison,
        "selected_model": "Random Forest",
        "best_params": grid.best_params_,
        "test_metrics": rf_metrics,
        "features": importances,
        "feature_order": FEATURE_ORDER,
        "medians": medians,
        "thresholds": {"low_max": 39, "mod_max": 69},
    }
    joblib.dump(best, OUT / "burnout_random_forest.joblib")
    joblib.dump({"medians": medians, "feature_order": FEATURE_ORDER}, OUT / "burnout_preprocessor.joblib")
    with open(OUT / "model_metadata.json", "w") as f:
        json.dump(meta, f, indent=2)
    print("saved", MODEL_VERSION, "test f1", rf_metrics["f1_macro"], "recall_high", rf_metrics["recall_high"])


if __name__ == "__main__":
    main()
