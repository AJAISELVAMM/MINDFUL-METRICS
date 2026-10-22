from __future__ import annotations

from datetime import date, timedelta
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from ..ml.burnout_model import score_from_proba
from ..ml.feature_engineering import FEATURE_ORDER, employee_feature_dict, assemble_matrix
from ..ml.model_loader import load_joblib, load_metadata, artifacts_ready
from ..models import Attendance, Communication, LeaveRequest, PermissionRequest, Prediction, Survey, PulseSurvey, Task, User, BurnoutFeatures
from ..config import MODEL_VERSION
from .recommendation_service import recommendations_from_factors
from .semantic_service import analyze_communication


def ensure_trained():
    if artifacts_ready():
        return
    import subprocess, sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    subprocess.check_call([sys.executable, str(root / "training" / "generate_synthetic_data.py")])
    subprocess.check_call([sys.executable, str(root / "training" / "train_text_model.py")])
    subprocess.check_call([sys.executable, str(root / "training" / "train_burnout_model.py")])


def _survey_scores(db: Session, user_id: int) -> dict | None:
    rows = (
        db.query(Survey)
        .filter(Survey.employee_id == user_id)
        .order_by(Survey.id.desc())
        .limit(14)
        .all()
    )
    pulse = (
        db.query(PulseSurvey)
        .filter(PulseSurvey.employee_id == user_id)
        .order_by(PulseSurvey.id.desc())
        .first()
    )

    if not rows and pulse is None:
        return None

    morning = next((s for s in rows if s.survey_type == "morning"), None)
    evening = next((s for s in rows if s.survey_type == "evening"), None)
    daily = next((s for s in rows if s.survey_type in ("daily", "manager", "hr")), None)

    a = {}
    if daily and daily.answers:
        a.update(daily.answers)
    if morning and morning.answers:
        a.update(morning.answers)
    if evening and evening.answers:
        a.update(evening.answers)

    def g(*keys, default=None):
        for k in keys:
            if k in a and a[k] is not None:
                try:
                    return float(a[k])
                except (TypeError, ValueError):
                    continue
        return default

    stress_val = g("stress")
    energy_val = g("energy", "energyLeft")
    mood_val = g("mood")
    wlb_val = g("wlb")
    sat_val = g("satisfied")
    workload_raw = g("workload")
    manageable_raw = g("manageable")
    personal_wl_raw = g("personal_workload")
    deadline_val = g("deadline", "blockers")
    diff_val = g("difficulty")
    ot_val = g("overtime", "overtime_mgmt")

    # Manager / HR question mappings fallback for stress and workload
    if stress_val is None:
        coordination = g("coordination")
        escalations = g("escalations")
        unexpected_mgmt = g("unexpected_mgmt")
        urgent_issues = g("urgent_issues")
        workforce_concerns = g("workforce_concerns")
        stress_items = [v for v in (coordination, escalations, unexpected_mgmt, urgent_issues, workforce_concerns) if v is not None]
        if stress_items:
            stress_val = float(np.mean(stress_items))

    # Perceived workload
    if workload_raw is not None:
        workload_score = (workload_raw / 5.0) * 100.0
    elif manageable_raw is not None:
        # 1=Overwhelming, 5=Manageable
        workload_score = ((6.0 - manageable_raw) / 5.0) * 100.0
    elif personal_wl_raw is not None:
        workload_score = ((6.0 - personal_wl_raw) / 5.0) * 100.0
    elif pulse is not None:
        p_map = {"Low": 25.0, "Moderate": 50.0, "High": 75.0, "Very High": 100.0}
        workload_score = p_map.get(pulse.workload_response, 50.0)
    else:
        workload_score = 50.0

    return {
        "stress": (stress_val / 5.0 * 100.0) if stress_val is not None else 50.0,
        "energy": (energy_val / 5.0 * 100.0) if energy_val is not None else 60.0,
        "mood": (mood_val / 5.0 * 100.0) if mood_val is not None else 60.0,
        "wlb": (wlb_val / 5.0 * 100.0) if wlb_val is not None else 55.0,
        "workload": workload_score,
        "deadline": (deadline_val / 5.0 * 100.0) if deadline_val is not None else 40.0,
        "difficulty": (diff_val / 5.0 * 100.0) if diff_val is not None else 50.0,
        "overtime": (ot_val / 5.0 * 8.0) if ot_val is not None else 0.5,
        "satisfaction": (sat_val / 5.0 * 100.0) if sat_val is not None else 60.0,
        "expected_wl": 50.0,
        "actual_wl": workload_score,
        "has_survey": bool(a) or (pulse is not None),
    }


def _attendance_feats(db: Session, user_id: int) -> dict:
    since = date.today() - timedelta(days=30)
    rows = (
        db.query(Attendance)
        .filter(Attendance.employee_id == user_id, Attendance.date >= since)
        .all()
    )
    if not rows:
        return {"hours": 8.0, "overtime": 0.0, "attendance": 95.0, "n": 0}

    # Only treat completed sessions as finished working time
    completed_rows = [
        r for r in rows
        if (r.working_minutes or 0) > 0 and r.check_out_at is not None and r.final_status not in ("INCOMPLETE", "WORKING")
    ]

    if completed_rows:
        hours = float(np.mean([r.working_minutes / 60.0 for r in completed_rows]))
        ot = float(np.mean([(r.overtime_minutes or 0) / 60.0 for r in completed_rows]))
    else:
        # Fallback to general recorded minutes or standard baseline
        valid_minutes = [r.working_minutes for r in rows if r.working_minutes and r.working_minutes > 0]
        hours = float(np.mean([m / 60.0 for m in valid_minutes])) if valid_minutes else 8.0
        valid_ot = [r.overtime_minutes for r in rows if r.overtime_minutes and r.overtime_minutes > 0]
        ot = float(np.mean([m / 60.0 for m in valid_ot])) if valid_ot else 0.0

    present = sum(
        1 for r in rows
        if r.status in ("Completed", "Working")
        or r.morning_status == "PRESENT"
        or r.final_status in ("FULL_DAY_PRESENT", "PRESENT_WITH_APPROVED_PERMISSION", "HALF_DAY_LEAVE")
    )
    attendance = float(100.0 * present / max(len(rows), 1))

    return {
        "hours": float(hours),
        "overtime": float(ot),
        "attendance": float(attendance),
        "n": len(rows),
    }


def _task_feats(db: Session, user_id: int) -> dict:
    tasks = db.query(Task).filter(Task.employee_id == user_id).all()
    if not tasks:
        return {
            "completion": 80.0,
            "difficulty": 50.0,
            "deadline_pressure": 35.0,
            "workload_deviation": 0.0,
            "n": 0,
        }

    # Strict rule: only completed tasks with completed status or 100% count as completed
    done = sum(1 for t in tasks if t.status == "Completed" or (t.completion_percentage == 100 or t.completed_at is not None))
    completion_rate = float(100.0 * done / len(tasks))

    diff = float(np.mean([t.difficulty or 3 for t in tasks]) * 20.0)

    # Deadline pressure from actual task deadlines
    pending_tasks = [t for t in tasks if t.status not in ("Completed", "Cancelled")]
    today_d = date.today()
    urgent_tasks = sum(
        1 for t in pending_tasks
        if t.status == "Overdue"
        or (t.due_date and t.due_date <= today_d)
        or t.priority in ("High", "Urgent")
        or "today" in (t.deadline or "").lower()
    )
    deadline_pressure = float(100.0 * urgent_tasks / max(len(pending_tasks), 1)) if pending_tasks else 25.0
    workload_deviation = float(min(30.0, max(-30.0, (len(pending_tasks) - 3) * 6.0)))

    return {
        "completion": completion_rate,
        "difficulty": diff,
        "deadline_pressure": deadline_pressure,
        "workload_deviation": workload_deviation,
        "n": len(tasks),
    }


def _comm_feats(db: Session, user_id: int) -> dict:
    rows = (
        db.query(Communication)
        .filter(Communication.employee_id == user_id)
        .order_by(Communication.id.desc())
        .limit(10)
        .all()
    )
    if not rows:
        return {
            "sentiment": 0.0,
            "cstress": 0.0,
            "cneg": 0.0,
            "sem_mean": 0.0,
            "sem_std": 0.0,
            "sem_norm": 0.0,
            "n": 0,
            "text": "",
        }

    text = " ".join(r.text.strip() for r in rows if r.text and r.text.strip())
    if text:
        sem = analyze_communication(text)
        return {
            "sentiment": float(sem.get("sentiment_score", 0.0)),
            "cstress": float(sem.get("stress_keyword_score", 0.0)),
            "cneg": float(sem.get("negative_language_score", 0.0)),
            "sem_mean": float(sem.get("sem_mean", 0.0)),
            "sem_std": float(sem.get("sem_std", 0.0)),
            "sem_norm": float(sem.get("sem_norm", 0.0)),
            "n": len(rows),
            "text": text[:500],
        }

    return {
        "sentiment": 0.0,
        "cstress": 0.0,
        "cneg": 0.0,
        "sem_mean": 0.0,
        "sem_std": 0.0,
        "sem_norm": 0.0,
        "n": len(rows),
        "text": "",
    }


def predict_for_employee(db: Session, user: User, persist: bool = True) -> dict:
    ensure_trained()
    surveys = _survey_scores(db, user.id)
    att = _attendance_feats(db, user.id)
    tasks = _task_feats(db, user.id)
    comm = _comm_feats(db, user.id)

    approved_leaves = (
        db.query(LeaveRequest)
        .filter(LeaveRequest.employee_id == user.id, LeaveRequest.status.in_(["Approved", "approved"]))
        .count()
    )
    approved_perms = (
        db.query(PermissionRequest)
        .filter(PermissionRequest.employee_id == user.id, PermissionRequest.status.in_(["Approved", "approved"]))
        .count()
    )
    leave_n = float(approved_leaves + approved_perms * 0.5)

    insufficient = surveys is None and att["n"] == 0 and comm["n"] == 0 and tasks["n"] == 0
    if insufficient:
        return {
            "employee_id": user.employee_code or user.id,
            "insufficient_data": True,
            "message": "Insufficient data for reliable prediction. Need a recent wellbeing survey, work information, or historical signals.",
            "model_version": MODEL_VERSION,
        }

    s = surveys or {
        "stress": 50.0,
        "energy": 60.0,
        "mood": 60.0,
        "wlb": 55.0,
        "workload": 50.0,
        "deadline": tasks.get("deadline_pressure", 35.0),
        "difficulty": tasks.get("difficulty", 50.0),
        "overtime": att["overtime"],
        "satisfaction": 60.0,
        "expected_wl": 50.0,
        "actual_wl": 50.0,
        "has_survey": False,
    }

    # Blend survey workload with task deadline and difficulty indicators
    deadline_val = float(tasks.get("deadline_pressure", s["deadline"])) if tasks["n"] > 0 else float(s["deadline"])
    difficulty_val = float(tasks.get("difficulty", s["difficulty"])) if tasks["n"] > 0 else float(s["difficulty"])
    workload_val = s["workload"]

    # Derived workload deviation:
    # Actual workload combines base perceived workload with task workload deviation
    exp_wl = 50.0
    act_wl = float(np.clip(workload_val + tasks.get("workload_deviation", 0.0), 0.0, 100.0))

    exp_h = 8.0
    act_h = att["hours"]
    overtime_val = s["overtime"] if s.get("has_survey") and s["overtime"] > 0 else att["overtime"]

    feat = employee_feature_dict(
        stress=s["stress"],
        workload=workload_val,
        wlb=s["wlb"],
        energy=s["energy"],
        mood=s["mood"],
        satisfaction=s["satisfaction"],
        hours=att["hours"],
        overtime=overtime_val,
        attendance=att["attendance"],
        leave_f=leave_n,
        completion=tasks["completion"],
        deadline=deadline_val,
        difficulty=difficulty_val,
        exp_wl=exp_wl,
        act_wl=act_wl,
        exp_h=exp_h,
        act_h=act_h,
        sentiment=comm["sentiment"],
        cstress=comm["cstress"],
        cneg=comm["cneg"],
        sem_mean=comm["sem_mean"],
        sem_std=comm["sem_std"],
        sem_norm=comm["sem_norm"],
    )

    X = assemble_matrix(pd.DataFrame([feat]))
    clf = load_joblib("burnout_random_forest.joblib")
    proba = clf.predict_proba(X)[0]
    score, level, probs, conf = score_from_proba(list(clf.classes_), proba)
    imps = sorted(zip(FEATURE_ORDER, clf.feature_importances_), key=lambda x: -x[1])
    factors = [
        {"feature": n, "importance": round(float(i), 4), "value": round(float(feat.get(n, 0)), 2)}
        for n, i in imps[:5]
    ]
    recs = recommendations_from_factors(factors, level)

    payload = {
        "employee_id": user.employee_code or user.id,
        "burnout_score": score,
        "risk_level": level,
        "confidence": round(conf, 3),
        "probabilities": probs,
        "risk_factors": factors,
        "recommendations": recs,
        "model_version": MODEL_VERSION,
        "insufficient_data": False,
        "explanation": f"Your current risk is mainly associated with {factors[0]['feature'].replace('_', ' ')}, {factors[1]['feature'].replace('_', ' ')} and {factors[2]['feature'].replace('_', ' ')}." if len(factors) >= 3 else "",
    }

    if persist:
        # Save or update Prediction
        db.add(Prediction(
            employee_id=user.id,
            burnout_score=score,
            risk_level=level,
            confidence=conf,
            model_version=MODEL_VERSION,
            top_factors=factors,
            recommendations=recs,
            probabilities=probs,
        ))

        # Save or update BurnoutFeatures for historical tracking
        today_d = date.today()
        existing_bf = (
            db.query(BurnoutFeatures)
            .filter(BurnoutFeatures.employee_id == user.id, BurnoutFeatures.date == today_d)
            .first()
        )
        if existing_bf:
            existing_bf.features = feat
        else:
            db.add(BurnoutFeatures(
                employee_id=user.id,
                date=today_d,
                features=feat,
            ))

        db.commit()

        # Phase 5: High burnout alert for HR and manager (deduplicated per day)
        if level == "HIGH" and (score or 0) >= 70:
            from .notification_service import create_notification, notify_hr_role
            # Notify HR
            notify_hr_role(
                db,
                title="High Burnout Risk Alert",
                body=f"High risk detected for {user.name} ({user.department or 'General'}) with score {int(score)}%.",
                notification_type="HIGH_BURNOUT_ALERT",
                entity_type="burnout",
                entity_id=user.id,
                priority="critical",
                link_url="/hr/risk-monitoring",
                dedup_key_prefix=f"hr_burnout_{user.id}_{today_d}",
            )
            # Phase 4.D: Notify manager if authorized team member
            if user.manager_id and user.manager_id != user.id:
                create_notification(
                    db,
                    recipient_id=user.manager_id,
                    title="Team Wellbeing Alert",
                    body=f"High workload and stress signal detected for team member in {user.department or 'your team'}.",
                    notification_type="TEAM_BURNOUT_ALERT",
                    entity_type="burnout",
                    entity_id=user.id,
                    priority="high",
                    link_url="/manager/burnout",
                    dedup_key=f"mgr_burnout_{user.manager_id}_{user.id}_{today_d}",
                )

    return payload


def recalculate_employee_burnout(
    db: Session,
    employee_id: int,
    trigger_source: str = "manual",
    actor: User | None = None,
    persist: bool = True,
) -> dict:
    """
    Authoritative Central Burnout Recalculation Service (Part 2 & 3).
    - Validates target employee exists and authorization of the caller.
    - Loads actual survey, attendance, task, and communication records for the employee.
    - Assembles the 21-feature vector in exact model feature order.
    - Executes the trained Random Forest inference pipeline.
    - Persists the prediction, risk factors, recommendations, and feature snapshot.
    - Dispatches alerts if qualifying high risk is reached.
    - Returns updated prediction results and derived KPI metrics.
    """
    target = db.query(User).filter(User.id == employee_id).first()
    if not target:
        raise ValueError(f"Employee {employee_id} not found.")

    if actor is not None:
        if actor.role == "employee" and actor.id != target.id:
            raise PermissionError("Unauthorized: Employees can only view/calculate their own burnout analytics.")
        elif actor.role == "manager":
            is_self = (target.id == actor.id)
            is_report = (target.manager_id == actor.id or target.manager_name == actor.name)
            is_emp = (target.role == "employee")
            if not (is_self or is_report or is_emp):
                raise PermissionError("Unauthorized: Managers can only view/calculate burnout for authorized team members.")

    result = predict_for_employee(db=db, user=target, persist=persist)

    # Attach derived KPI snapshots for easy consumption by callers
    latest_bf = (
        db.query(BurnoutFeatures)
        .filter(BurnoutFeatures.employee_id == target.id)
        .order_by(BurnoutFeatures.id.desc())
        .first()
    )
    feat_dict = latest_bf.features if latest_bf and latest_bf.features else {}

    result["kpis"] = {
        "burnoutRisk": result.get("burnout_score", 50),
        "burnoutLabel": result.get("risk_level", "MODERATE"),
        "workloadScore": round(feat_dict.get("workload_score", 50)),
        "wlbScore": round(feat_dict.get("work_life_balance_score", 50)),
        "stressScore": round(feat_dict.get("stress_score", 50)),
        "workingHours": round(feat_dict.get("working_hours", 8.0), 1),
    }
    result["trigger_source"] = trigger_source
    return result


def get_employee_core_metrics(db: Session, employee: User) -> dict:
    """
    Authoritative single source of truth for individual employee metrics.
    Guarantees consistent, database-backed calculation across:
    1. Employee Dashboard (_kpis_for)
    2. HR Employee Detail Drawer (get_user_full_details)
    3. Manager Employee Detail Drawer (get_user_full_details)
    4. HR Employees Table (hr_emp)
    5. Manager Team Dashboard (mgr_dash)
    6. Manager Team Workload Table (get_team_workload_metrics)
    """
    # 1. Prediction / Burnout
    latest_pred = (
        db.query(Prediction)
        .filter(Prediction.employee_id == employee.id)
        .order_by(Prediction.id.desc())
        .first()
    )
    if not latest_pred:
        try:
            pred_gen = predict_for_employee(db, employee, persist=True)
            if not pred_gen.get("insufficient_data"):
                latest_pred = (
                    db.query(Prediction)
                    .filter(Prediction.employee_id == employee.id)
                    .order_by(Prediction.id.desc())
                    .first()
                )
        except Exception:
            pass

    burnout_score = int(round(latest_pred.burnout_score)) if (latest_pred and latest_pred.burnout_score is not None) else None
    if burnout_score is not None:
        risk_level = (
            "HIGH" if burnout_score >= 70
            else ("MODERATE" if burnout_score >= 40 else "LOW")
        )
    else:
        risk_level = "Unavailable"

    # 2. Features snapshot & latest survey answers
    latest_bf = (
        db.query(BurnoutFeatures)
        .filter(BurnoutFeatures.employee_id == employee.id)
        .order_by(BurnoutFeatures.id.desc())
        .first()
    )
    feat_dict = latest_bf.features if latest_bf and isinstance(latest_bf.features, dict) else {}

    latest_survey = (
        db.query(Survey)
        .filter(Survey.employee_id == employee.id)
        .order_by(Survey.id.desc())
        .first()
    )
    survey_ans = latest_survey.answers if latest_survey and isinstance(latest_survey.answers, dict) else {}

    # 3. Authoritative Task records
    tasks = db.query(Task).filter(Task.employee_id == employee.id).all()
    total_tasks = len(tasks)
    completed_tasks = [t for t in tasks if t.status in ("Completed", "Done")]
    active_tasks = [t for t in tasks if t.status not in ("Completed", "Done")]
    blocked_tasks = [t for t in tasks if t.status == "Blocked" or (t.blocked_reason and t.status not in ("Completed", "Done"))]
    overdue_tasks = [t for t in tasks if t.status == "Overdue"]
    completion_rate = round(len(completed_tasks) / total_tasks * 100) if total_tasks else 0

    # 4. Workload Score (consistent dynamic formulation)
    if "workload" in survey_ans:
        base_wl = float(survey_ans["workload"]) * 20.0
    elif "manageable" in survey_ans:
        base_wl = (6.0 - float(survey_ans["manageable"])) * 20.0
    elif feat_dict.get("workload_score") is not None:
        base_wl = float(feat_dict["workload_score"])
    elif burnout_score is not None:
        base_wl = float(burnout_score)
    else:
        base_wl = 50.0

    if tasks:
        wl_dev = min(30.0, max(-30.0, (len(active_tasks) - 3) * 6.0))
        workload_score = int(round(min(100.0, max(0.0, base_wl + wl_dev))))
    elif feat_dict.get("workload_score") is not None:
        workload_score = int(round(float(feat_dict["workload_score"])))
    elif survey_ans:
        workload_score = int(round(min(100.0, max(0.0, base_wl))))
    elif burnout_score is not None:
        workload_score = int(round(min(100.0, max(20.0, burnout_score * 0.85))))
    else:
        workload_score = None

    # 5. Recent Attendance for working hours, overtime, and work-life balance
    recent_att = (
        db.query(Attendance)
        .filter(Attendance.employee_id == employee.id)
        .order_by(Attendance.date.desc())
        .limit(14)
        .all()
    )
    valid_att = [a for a in recent_att if a.working_minutes and a.working_minutes > 0]
    if valid_att:
        avg_minutes = sum(a.working_minutes for a in valid_att) / len(valid_att)
        working_hours_num = round(avg_minutes / 60.0, 1)
        working_hours_display = f"{working_hours_num}h"
        ot_minutes = sum(a.overtime_minutes or 0 for a in valid_att) / len(valid_att)
        ot_hours_num = round(ot_minutes / 60.0, 1)
    elif feat_dict.get("working_hours") is not None:
        working_hours_num = round(float(feat_dict["working_hours"]), 1)
        working_hours_display = f"{working_hours_num}h"
        ot_hours_num = round(float(feat_dict.get("overtime_hours", 0)), 1)
    else:
        working_hours_num = None
        working_hours_display = None
        ot_hours_num = 0.0

    # 6. Work-Life Balance Score
    if "wlb" in survey_ans:
        wlb_score = int(round(float(survey_ans["wlb"]) * 20.0))
    elif feat_dict.get("work_life_balance_score") is not None:
        wlb_score = int(round(float(feat_dict["work_life_balance_score"])))
    elif recent_att or burnout_score is not None:
        recent_ot_h = (
            sum((a.overtime_minutes or 0) for a in recent_att) / max(len(recent_att), 1) / 60.0
            if recent_att else 0.0
        )
        base_s = float(burnout_score if burnout_score is not None else 50.0)
        wlb_score = int(round(max(20.0, min(100.0, 100.0 - (base_s * 0.5) - (recent_ot_h * 5.0)))))
    else:
        wlb_score = None

    # 7. Stress Score
    if "stress" in survey_ans:
        stress_score = int(round(float(survey_ans["stress"]) * 20.0))
    elif feat_dict.get("stress_score") is not None:
        stress_score = int(round(float(feat_dict["stress_score"])))
    elif burnout_score is not None:
        stress_score = int(round(min(100.0, max(20.0, burnout_score * 0.92))))
    else:
        stress_score = None

    # 8. Factors and recommendations
    factors = [
        {"name": f.get("feature", f.get("name", "")).replace("_", " ").title(), "impact": f.get("importance", 0)}
        for f in (latest_pred.top_factors or [])
    ] if latest_pred else []

    recs_list = (latest_pred.recommendations or []) if latest_pred else []
    if not recs_list and latest_pred and latest_pred.top_factors:
        recs_list = recommendations_from_factors(latest_pred.top_factors, risk_level)

    pred_time = getattr(latest_pred, "prediction_date", None) or getattr(latest_pred, "created_at", None)

    return {
        "user_id": employee.id,
        "employee_code": employee.employee_code or f"E{employee.id}",
        "name": employee.name,
        "department": employee.department or "Engineering",
        "role": employee.role or "employee",
        "burnout_score": burnout_score,
        "risk_level": risk_level,
        "stress_score": stress_score,
        "workload_score": workload_score,
        "wlb_score": wlb_score,
        "working_hours_num": working_hours_num,
        "working_hours_display": working_hours_display,
        "overtime_hours_num": ot_hours_num,
        "total_tasks": total_tasks,
        "active_tasks": len(active_tasks),
        "completed_tasks": len(completed_tasks),
        "blocked_tasks": len(blocked_tasks),
        "overdue_tasks": len(overdue_tasks),
        "completion_rate": completion_rate,
        "prediction_timestamp": pred_time.strftime("%d %b %Y, %I:%M %p") if pred_time else None,
        "risk_factors": factors,
        "recommendations": recs_list,
        "explanation": getattr(latest_pred, "explanation", None) or (recs_list[0] if recs_list else ""),
        "has_prediction": latest_pred is not None and burnout_score is not None,
    }


