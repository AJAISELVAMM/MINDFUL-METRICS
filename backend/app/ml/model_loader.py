from __future__ import annotations

import json
import os
from functools import lru_cache

import joblib

from ..config import MODEL_DIR

_cache = {}


def _p(name: str) -> str:
    return os.path.join(MODEL_DIR, name)


def load_joblib(name: str):
    path = _p(name)
    if name not in _cache:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Model artifact missing: {path}. Run training scripts.")
        _cache[name] = joblib.load(path)
    return _cache[name]


def load_metadata() -> dict:
    path = _p("model_metadata.json")
    if not os.path.exists(path):
        return {"disclaimer": "Models not trained yet."}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def artifacts_ready() -> bool:
    needed = [
        "burnout_random_forest.joblib",
        "text_tfidf_logreg.joblib",
        "semantic_encoder.joblib",
        "model_metadata.json",
    ]
    return all(os.path.exists(_p(n)) for n in needed)
