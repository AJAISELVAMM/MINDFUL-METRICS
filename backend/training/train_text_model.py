"""Train TF-IDF + Logistic Regression on synthetic communications."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix, f1_score, precision_score, recall_score, accuracy_score
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.ml.text_classifier import build_text_pipeline  # noqa: E402
from app.ml.semantic_model import SemanticEncoder  # noqa: E402

DS = ROOT / "datasets" / "communication_training.csv"
OUT = ROOT / "models"
OUT.mkdir(exist_ok=True)


def main():
    df = pd.read_csv(DS)
    df["text"] = df["text"].fillna("").astype(str)
    Xtr, Xte, ytr, yte = train_test_split(
        df["text"], df["stress_class"], test_size=0.2, random_state=42, stratify=df["stress_class"]
    )
    pipe = build_text_pipeline()
    pipe.fit(Xtr, ytr)
    pred = pipe.predict(Xte)
    metrics = {
        "accuracy": float(accuracy_score(yte, pred)),
        "precision_macro": float(precision_score(yte, pred, average="macro", zero_division=0)),
        "recall_macro": float(recall_score(yte, pred, average="macro", zero_division=0)),
        "f1_macro": float(f1_score(yte, pred, average="macro", zero_division=0)),
        "classification_report": classification_report(yte, pred, output_dict=True, zero_division=0),
        "confusion_matrix": confusion_matrix(yte, pred, labels=["LOW_STRESS", "MODERATE_STRESS", "HIGH_STRESS"]).tolist(),
        "labels": ["LOW_STRESS", "MODERATE_STRESS", "HIGH_STRESS"],
        "dataset": "synthetic_v1",
        "n": int(len(df)),
    }
    joblib.dump(pipe, OUT / "text_tfidf_logreg.joblib")
    enc = SemanticEncoder().fit(df["text"].tolist())
    joblib.dump(enc, OUT / "semantic_encoder.joblib")
    with open(OUT / "text_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
    print("text model", metrics["accuracy"], metrics["f1_macro"], "semantic", enc.backend)


if __name__ == "__main__":
    main()
