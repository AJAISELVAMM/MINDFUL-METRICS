from __future__ import annotations

import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier

from ..config import LOW_MAX, MOD_MAX

LABELS = ["LOW", "MODERATE", "HIGH"]


def build_random_forest(**params) -> RandomForestClassifier:
    defaults = dict(
        n_estimators=180,
        max_depth=10,
        min_samples_split=4,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    defaults.update(params)
    return RandomForestClassifier(**defaults)


def baselines():
    return {
        "Logistic Regression": LogisticRegression(max_iter=500, class_weight="balanced", random_state=42),
        "Gradient Boosting": GradientBoostingClassifier(n_estimators=100, max_depth=4, random_state=42),
        "Decision Tree": DecisionTreeClassifier(max_depth=8, class_weight="balanced", random_state=42),
        "Random Forest": build_random_forest(),
    }


def score_from_proba(classes: list[str], proba: np.ndarray) -> tuple[float, str, dict, float]:
    mapping = {c: float(p) for c, p in zip(classes, proba)}
    p_low = mapping.get("LOW", 0.0)
    p_mod = mapping.get("MODERATE", 0.0)
    p_high = mapping.get("HIGH", 0.0)
    # Documented mapping: expected class midpoints
    score = p_low * 20 + p_mod * 60 + p_high * 90
    score = float(max(0, min(100, round(score, 1))))
    if score <= LOW_MAX:
        level = "LOW"
    elif score <= MOD_MAX:
        level = "MODERATE"
    else:
        level = "HIGH"
    conf = float(max(mapping.values())) if mapping else 0.0
    return score, level, {"low": p_low, "moderate": p_mod, "high": p_high}, conf
