from __future__ import annotations

import numpy as np
import pandas as pd
from .preprocessing import STRUCT_FEATURES

FEATURE_ORDER = STRUCT_FEATURES + [
    "communication_sentiment",
    "communication_stress_score",
    "communication_negative_score",
    "sem_mean",
    "sem_std",
    "sem_norm",
]


def assemble_matrix(df: pd.DataFrame, sem_derived: np.ndarray | None = None) -> pd.DataFrame:
    out = pd.DataFrame()
    for c in STRUCT_FEATURES:
        out[c] = pd.to_numeric(df[c], errors="coerce") if c in df.columns else 0.0
    for c in ["communication_sentiment", "communication_stress_score", "communication_negative_score"]:
        out[c] = pd.to_numeric(df[c], errors="coerce") if c in df.columns else 0.0
    if sem_derived is not None and len(sem_derived):
        out["sem_mean"] = sem_derived[:, 0]
        out["sem_std"] = sem_derived[:, 1]
        out["sem_norm"] = sem_derived[:, 2]
    else:
        out["sem_mean"] = 0.0
        out["sem_std"] = 0.0
        out["sem_norm"] = 0.0
    return out[FEATURE_ORDER]


def employee_feature_dict(
    *,
    stress=50, workload=50, wlb=50, energy=50, mood=50, satisfaction=50,
    hours=8, overtime=0, attendance=95, leave_f=1,
    completion=80, deadline=40, difficulty=40,
    exp_wl=50, act_wl=50, exp_h=8, act_h=8,
    sentiment=0.0, cstress=0.0, cneg=0.0,
    sem_mean=0.0, sem_std=0.0, sem_norm=0.0,
) -> dict:
    return {
        "stress_score": float(stress),
        "workload_score": float(workload),
        "work_life_balance_score": float(wlb),
        "energy_score": float(energy),
        "mood_score": float(mood),
        "job_satisfaction_score": float(satisfaction),
        "working_hours": float(hours),
        "overtime_hours": float(overtime),
        "attendance_rate": float(attendance),
        "leave_frequency": float(leave_f),
        "task_completion_rate": float(completion),
        "deadline_pressure": float(deadline),
        "task_difficulty": float(difficulty),
        "workload_deviation": float(act_wl) - float(exp_wl),
        "working_hour_deviation": float(act_h) - float(exp_h),
        "communication_sentiment": float(sentiment),
        "communication_stress_score": float(cstress),
        "communication_negative_score": float(cneg),
        "sem_mean": float(sem_mean),
        "sem_std": float(sem_std),
        "sem_norm": float(sem_norm),
    }
