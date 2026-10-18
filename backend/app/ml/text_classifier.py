from __future__ import annotations

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline


def build_text_pipeline() -> Pipeline:
    return Pipeline(
        [
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1, max_features=5000, lowercase=True)),
            ("clf", LogisticRegression(max_iter=400, class_weight="balanced", random_state=42)),
        ]
    )


def predict_text(pipe: Pipeline, text: str) -> dict:
    text = (text or "").strip()
    if not text:
        return {
            "sentiment": "NEUTRAL",
            "stress_class": "LOW_STRESS",
            "stress_language_probability": 0.0,
            "negative_language_probability": 0.0,
            "communication_risk_score": 0.0,
            "insufficient_text": True,
        }
    proba = pipe.predict_proba([text])[0]
    classes = list(pipe.named_steps["clf"].classes_)
    mapping = {c: float(p) for c, p in zip(classes, proba)}
    pred = classes[int(np.argmax(proba))]
    high = mapping.get("HIGH_STRESS", mapping.get("NEGATIVE", 0.0))
    neg = mapping.get("NEGATIVE", mapping.get("HIGH_STRESS", 0.0))
    return {
        "sentiment": "NEGATIVE" if high > 0.55 else ("POSITIVE" if mapping.get("LOW_STRESS", 0) > 0.55 else "NEUTRAL"),
        "stress_class": pred if "STRESS" in str(pred) else "MODERATE_STRESS",
        "stress_language_probability": round(high, 3),
        "negative_language_probability": round(neg, 3),
        "communication_risk_score": round(high, 3),
        "class_probabilities": mapping,
        "insufficient_text": False,
    }
