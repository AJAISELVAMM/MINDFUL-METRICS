from __future__ import annotations
from functools import lru_cache

from ..ml.model_loader import load_joblib
from ..ml.text_classifier import predict_text
from ..ml.semantic_model import SemanticEncoder


@lru_cache(maxsize=512)
def analyze_communication(text: str) -> dict:
    text = (text or "").strip()
    if not text:
        return {
            "sentiment_score": 0.0,
            "stress_keyword_score": 0.0,
            "workload_language_score": 0.0,
            "negative_language_score": 0.0,
            "insufficient_text": True,
        }
    clf = load_joblib("text_tfidf_logreg.joblib")
    enc: SemanticEncoder = load_joblib("semantic_encoder.joblib")
    t = predict_text(clf, text)
    derived = enc.derived_features([text])[0]
    return {
        "sentiment": t["sentiment"],
        "stress_class": t.get("stress_class"),
        "sentiment_score": -t["negative_language_probability"] if t["sentiment"] == "NEGATIVE" else (0.4 if t["sentiment"] == "POSITIVE" else 0.0),
        "stress_keyword_score": t["stress_language_probability"],
        "workload_language_score": t["communication_risk_score"],
        "negative_language_score": t["negative_language_probability"],
        "communication_risk_score": t["communication_risk_score"],
        "sem_mean": float(derived[0]),
        "sem_std": float(derived[1]),
        "sem_norm": float(derived[2]),
        "insufficient_text": False,
        "class_probabilities": t.get("class_probabilities", {}),
    }
