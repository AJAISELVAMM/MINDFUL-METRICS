from __future__ import annotations

import numpy as np
import pandas as pd

STRUCT_FEATURES = [
    "stress_score",
    "workload_score",
    "work_life_balance_score",
    "energy_score",
    "mood_score",
    "job_satisfaction_score",
    "working_hours",
    "overtime_hours",
    "attendance_rate",
    "leave_frequency",
    "task_completion_rate",
    "deadline_pressure",
    "task_difficulty",
    "workload_deviation",
    "working_hour_deviation",
]

RANGES = {
    "stress_score": (0, 100),
    "workload_score": (0, 100),
    "work_life_balance_score": (0, 100),
    "energy_score": (0, 100),
    "mood_score": (0, 100),
    "job_satisfaction_score": (0, 100),
    "working_hours": (0, 16),
    "overtime_hours": (0, 24),
    "attendance_rate": (0, 100),
}


def validate_frame(df: pd.DataFrame, require_label: bool = True) -> pd.DataFrame:
    out = df.copy()
    if require_label and "burnout_label" not in out.columns:
        raise ValueError("burnout_label missing")
    out = out.drop_duplicates()
    for col, (lo, hi) in RANGES.items():
        if col in out.columns:
            out[col] = out[col].clip(lo, hi)
    for c in STRUCT_FEATURES:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")
    out = out.dropna(subset=[c for c in STRUCT_FEATURES if c in out.columns], how="any")
    return out


def impute_numeric(df: pd.DataFrame, medians: dict | None = None) -> tuple[pd.DataFrame, dict]:
    out = df.copy()
    med = medians or {}
    for c in STRUCT_FEATURES:
        if c not in out.columns:
            continue
        if c not in med:
            med[c] = float(out[c].median()) if len(out) else 50.0
        out[c] = out[c].fillna(med[c])
    return out, med
