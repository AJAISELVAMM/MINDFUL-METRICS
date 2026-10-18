from __future__ import annotations
from datetime import date, datetime
from sqlalchemy.orm import Session
from ..models import Survey, PulseSurvey, Communication, User
from .semantic_service import analyze_communication
from .burnout_service import predict_for_employee, recalculate_employee_burnout
from .audit_service import log_audit


EMPLOYEE_SURVEY_QUESTIONS = {
    "wellbeing": [
        {"id": "stress", "label": "How stressed do you feel today?", "low": "Calm (1)", "high": "Very stressed (5)"},
        {"id": "energy", "label": "How is your energy level?", "low": "Drained (1)", "high": "Energized (5)"},
        {"id": "manageable", "label": "How manageable is your workload?", "low": "Overwhelming (1)", "high": "Manageable (5)"},
        {"id": "satisfied", "label": "How is your work satisfaction today?", "low": "Low (1)", "high": "High (5)"},
        {"id": "wlb", "label": "How is your work-life balance currently?", "low": "Poor (1)", "high": "Balanced (5)"},
    ],
    "work": [
        {"id": "main_task", "label": "Main task focus today?", "type": "text"},
        {"id": "completion", "label": "Expected task completion rate?", "low": "Low (1)", "high": "Complete (5)"},
        {"id": "difficulty", "label": "How difficult are today's tasks?", "low": "Easy (1)", "high": "Very hard (5)"},
        {"id": "blockers", "label": "Are there blockers hindering progress?", "low": "None (1)", "high": "Severe (5)"},
        {"id": "unexpected", "label": "Did unexpected tasks arise today?", "low": "None (1)", "high": "Many (5)"},
        {"id": "overtime", "label": "Likelihood of working extended hours?", "low": "Unlikely (1)", "high": "Definite (5)"},
    ],
}

MANAGER_SURVEY_QUESTIONS = {
    "management": [
        {"id": "team_workload", "label": "How manageable is your team's workload?", "low": "Overwhelming (1)", "high": "Manageable (5)"},
        {"id": "meeting_load", "label": "How heavy was your meeting schedule today?", "low": "Light (1)", "high": "Exhausting (5)"},
        {"id": "team_support", "label": "Level of team support / firefighting required?", "low": "Minimal (1)", "high": "Extensive (5)"},
        {"id": "escalations", "label": "Number of critical escalations or blocker issues?", "low": "None (1)", "high": "Multiple (5)"},
        {"id": "coordination", "label": "Coordination difficulty across team & stakeholders?", "low": "Smooth (1)", "high": "Challenging (5)"},
        {"id": "unexpected_mgmt", "label": "Unexpected management/administrative overhead?", "low": "None (1)", "high": "High (5)"},
        {"id": "personal_workload", "label": "How is your personal workload manageability?", "low": "Overloaded (1)", "high": "Balanced (5)"},
        {"id": "overtime_mgmt", "label": "Need for after-hours work or work extension today?", "low": "None (1)", "high": "Significant (5)"},
    ]
}

HR_SURVEY_QUESTIONS = {
    "hr": [
        {"id": "hr_workload", "label": "How manageable is your HR operations workload?", "low": "Heavy (1)", "high": "Manageable (5)"},
        {"id": "requests_handled", "label": "Volume of employee requests & grievances handled?", "low": "Low (1)", "high": "High (5)"},
        {"id": "urgent_issues", "label": "Urgent workforce or compliance issues requiring resolution?", "low": "None (1)", "high": "Multiple (5)"},
        {"id": "workforce_concerns", "label": "Workforce morale & wellbeing concerns observed?", "low": "None (1)", "high": "Elevated (5)"},
        {"id": "admin_workload", "label": "Administrative overhead versus strategic tasks?", "low": "Balanced (1)", "high": "Overloaded (5)"},
        {"id": "wlb", "label": "Your personal work-life balance today?", "low": "Strained (1)", "high": "Balanced (5)"},
    ]
}


def get_survey_questions_for_role(role: str) -> dict:
    base = {
        "wellbeing": EMPLOYEE_SURVEY_QUESTIONS["wellbeing"],
        "work": EMPLOYEE_SURVEY_QUESTIONS["work"],
    }
    if role == "manager":
        base["management"] = MANAGER_SURVEY_QUESTIONS["management"]
    elif role == "hr":
        base["hr"] = HR_SURVEY_QUESTIONS["hr"]
    return base


def submit_daily_survey(
    db: Session,
    user: User,
    answers: dict,
    note: str | None = None,
    survey_type: str = "daily",
) -> dict:
    today = date.today()
    existing = (
        db.query(Survey)
        .filter(Survey.employee_id == user.id, Survey.date == today, Survey.survey_type == survey_type)
        .first()
    )

    if existing:
        existing.answers = answers
        existing.note = note or existing.note
        existing.created_at = datetime.utcnow()
    else:
        existing = Survey(
            employee_id=user.id,
            date=today,
            survey_type=survey_type,
            role=user.role,
            answers=answers,
            note=note,
            created_at=datetime.utcnow(),
        )
        db.add(existing)

    if note and note.strip():
        existing_comm = (
            db.query(Communication)
            .filter(
                Communication.employee_id == user.id,
                Communication.source == survey_type,
                Communication.text == note.strip(),
            )
            .first()
        )
        if not existing_comm:
            sem = analyze_communication(note)
            comm = Communication(
                employee_id=user.id,
                text=note.strip(),
                source=survey_type,
                sentiment_score=sem.get("sentiment_score", 0),
                stress_keyword_score=sem.get("stress_keyword_score", 0),
                timestamp=datetime.utcnow(),
            )
            db.add(comm)

    db.commit()

    log_audit(
        db,
        actor=user,
        action="SURVEY_SUBMITTED",
        target_type="daily_survey",
        target_id=existing.id,
        new_value={"type": survey_type, "note_length": len(note or "")},
    )

    # Re-run prediction using central analysis service (Part 2.2.A)
    pred = recalculate_employee_burnout(db, user.id, trigger_source=f"survey_{survey_type}", actor=user, persist=True)
    return {"ok": True, "prediction": pred, "survey_id": existing.id}


def submit_pulse_survey(db: Session, user: User, workload_response: str) -> dict:
    today = date.today()
    valid = ["Low", "Moderate", "High", "Very High"]
    if workload_response not in valid:
        workload_response = "Moderate"

    existing = (
        db.query(PulseSurvey)
        .filter(PulseSurvey.employee_id == user.id, PulseSurvey.date == today)
        .first()
    )
    if existing:
        existing.workload_response = workload_response
    else:
        existing = PulseSurvey(
            employee_id=user.id,
            date=today,
            workload_response=workload_response,
            created_at=datetime.utcnow(),
        )
        db.add(existing)

    db.commit()

    # Re-run prediction using central analysis service (Part 2.2.A)
    try:
        pred = recalculate_employee_burnout(db, user.id, trigger_source="pulse_survey", actor=user, persist=True)
    except Exception:
        pred = None

    return {"ok": True, "date": str(today), "workload_response": workload_response, "prediction": pred}


def get_today_survey_status(db: Session, user: User) -> dict:
    today = date.today()
    surveys = (
        db.query(Survey)
        .filter(Survey.employee_id == user.id, Survey.date == today)
        .all()
    )
    pulse = (
        db.query(PulseSurvey)
        .filter(PulseSurvey.employee_id == user.id, PulseSurvey.date == today)
        .first()
    )

    has_daily = any(s.survey_type in ("daily", "morning") for s in surveys)
    has_evening = any(s.survey_type == "evening" for s in surveys)

    return {
        "dailyCompleted": has_daily,
        "eveningCompleted": has_evening,
        "pulseCompleted": bool(pulse),
        "pulseValue": pulse.workload_response if pulse else None,
        "count": len(surveys),
    }
