"""
MINDFUL METRICS - Comprehensive End-to-End Simulation & Verification Suite
Tests:
1. Dynamic Burnout Model (Test 1: Escalation, Test 2: Recovery, Test 3: Stability)
2. AI Assistant queries across Employee, Manager, and HR personas
3. Dashboard APIs & RBAC enforcement across roles
4. Automated pytest suite with safe execution
"""

from __future__ import annotations
import sys
import json
from datetime import date, datetime, time, timedelta
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.database import SessionLocal
from app.models import (
    User, Department, CompanySettings, Attendance, LeaveRequest,
    PermissionRequest, Task, Survey, PulseSurvey, Communication,
    Prediction
)
from app.services.attendance_service import get_company_settings, calculate_attendance_rule
from app.services.semantic_service import analyze_communication
from app.services.burnout_service import predict_for_employee, _survey_scores, _attendance_feats, _task_feats, _comm_feats
from app.services.ai_chat_service import process_chat_request
from app.main import app
from app.security import create_token
from fastapi.testclient import TestClient

client = TestClient(app)


def fmt_12h(dt: datetime) -> str:
    return dt.strftime("%I:%M %p")


def run_dynamic_burnout_tests():
    print("\n" + "=" * 60)
    print("SECTION 1: DYNAMIC BURNOUT MODEL VERIFICATION")
    print("=" * 60)
    db = SessionLocal()
    settings = get_company_settings(db)
    today = date.today()
    results = {}

    try:
        # -------------------------------------------------------------
        # TEST 1: Workload Escalation (Employee: Naveen - Engineering)
        # Starts LOW risk, increases workload/overtime/stress -> shifts upward
        # -------------------------------------------------------------
        emp1 = db.query(User).filter(User.email == "naveen@gmail.com").first()
        assert emp1, "Naveen not found"
        print(f"\n--- TEST 1: Workload Escalation for {emp1.name} ({emp1.email}) ---")

        pred_before_1 = predict_for_employee(db, emp1, persist=False)
        print(f"BEFORE: Score = {pred_before_1['burnout_score']}, Risk = {pred_before_1['risk_level']}, Probabilities = {pred_before_1['probabilities']}")

        # 1. Add 3 high difficulty/urgent tasks
        for k in range(3):
            t = Task(
                employee_id=emp1.id,
                assigned_by_id=emp1.manager_id,
                assigned_by_name=emp1.manager_name,
                name=f"Urgent High-Priority Hotfix #{k+1}",
                description="Production incident resolution requiring overtime.",
                priority="Urgent",
                difficulty=5,
                start_date=today - timedelta(days=2),
                due_date=today + timedelta(days=1),
                deadline=(today + timedelta(days=1)).isoformat(),
                status="Blocked" if k == 0 else "In Progress",
                completion_percentage=20,
                work_update="Struggling with blocking database errors and tight deadline.",
                blocked_reason="Blocked by downstream auth service timeout." if k == 0 else None,
                created_at=datetime.utcnow(),
            )
            db.add(t)

        # 2. Add heavy overtime attendance for past 3 days
        for offset in [0, 1, 2]:
            d = today - timedelta(days=offset)
            cin = datetime.combine(d, time(9, 20))
            cout = datetime.combine(d, time(19, 45))  # 135 mins overtime
            calc = calculate_attendance_rule(settings, cin, cout)
            existing_att = db.query(Attendance).filter(Attendance.employee_id == emp1.id, Attendance.date == d).first()
            if existing_att:
                existing_att.check_in_at = cin
                existing_att.check_out_at = cout
                existing_att.check_in = fmt_12h(cin)
                existing_att.check_out = fmt_12h(cout)
                existing_att.working_minutes = calc["working_minutes"]
                existing_att.overtime_minutes = calc["overtime_minutes"]
                existing_att.late_minutes = calc["late_minutes"]
                existing_att.final_status = calc["final_status"]
            else:
                db.add(Attendance(
                    employee_id=emp1.id, date=d, check_in=fmt_12h(cin), check_out=fmt_12h(cout),
                    check_in_at=cin, check_out_at=cout, working_minutes=calc["working_minutes"],
                    overtime_minutes=calc["overtime_minutes"], late_minutes=calc["late_minutes"],
                    morning_status=calc["morning_status"], afternoon_status=calc["afternoon_status"],
                    final_status=calc["final_status"], status="Completed"
                ))

        # 3. Add high-stress survey
        db.add(Survey(
            employee_id=emp1.id, date=today, survey_type="morning", role="employee",
            answers={"stress": 5, "energy": 1, "manageable": 1, "satisfied": 2, "wlb": 1},
            created_at=datetime.utcnow()
        ))
        db.add(Survey(
            employee_id=emp1.id, date=today, survey_type="evening", role="employee",
            answers={"difficulty": 5, "deadline": 5, "overtime": 5, "workload": 5, "completion": 2},
            created_at=datetime.utcnow()
        ))

        # 4. Add stressed communication through semantic pipeline
        stress_comm_text = "I have been working late for several days and there are too many critical tasks pending."
        sem1 = analyze_communication(stress_comm_text)
        db.add(Communication(
            employee_id=emp1.id, text=stress_comm_text, source="reflection",
            sentiment_score=sem1["sentiment_score"], stress_keyword_score=sem1["stress_keyword_score"],
            timestamp=datetime.utcnow()
        ))
        db.commit()

        pred_after_1 = predict_for_employee(db, emp1, persist=True)
        print(f"AFTER:  Score = {pred_after_1['burnout_score']}, Risk = {pred_after_1['risk_level']}, Probabilities = {pred_after_1['probabilities']}")
        print(f"Top Contributing Factors: {[f['feature'] for f in pred_after_1['risk_factors'][:3]]}")
        assert pred_after_1["burnout_score"] > pred_before_1["burnout_score"], "Prediction score did not increase after workload escalation!"
        results["test_1"] = {
            "employee": emp1.name,
            "before_score": pred_before_1["burnout_score"],
            "before_risk": pred_before_1["risk_level"],
            "after_score": pred_after_1["burnout_score"],
            "after_risk": pred_after_1["risk_level"],
            "top_factors": [f["feature"] for f in pred_after_1["risk_factors"][:3]],
            "delta": round(pred_after_1["burnout_score"] - pred_before_1["burnout_score"], 1),
        }

        # -------------------------------------------------------------
        # TEST 2: Workload Relief & Recovery (Employee: Pavithra - Engineering)
        # Starts HIGH risk, recovers via completed tasks, normal hours, positive signals
        # -------------------------------------------------------------
        emp2 = db.query(User).filter(User.email == "pavithra@gmail.com").first()
        assert emp2, "Pavithra not found"
        print(f"\n--- TEST 2: Workload Relief & Recovery for {emp2.name} ({emp2.email}) ---")

        pred_before_2 = predict_for_employee(db, emp2, persist=False)
        print(f"BEFORE: Score = {pred_before_2['burnout_score']}, Risk = {pred_before_2['risk_level']}, Probabilities = {pred_before_2['probabilities']}")

        # 1. Complete all pending tasks
        pending_tasks = db.query(Task).filter(Task.employee_id == emp2.id, Task.status != "Completed").all()
        for t in pending_tasks:
            t.status = "Completed"
            t.completion_percentage = 100
            t.blocked_reason = None
            t.work_update = "Deliverables completed and deployed successfully."
            t.completed_at = datetime.utcnow()

        # 2. Update attendance to normal balanced hours (09:10 - 17:15, 0 overtime)
        for offset in [0, 1, 2, 3]:
            d = today - timedelta(days=offset)
            cin = datetime.combine(d, time(9, 10))
            cout = datetime.combine(d, time(17, 15))
            calc = calculate_attendance_rule(settings, cin, cout)
            existing_att = db.query(Attendance).filter(Attendance.employee_id == emp2.id, Attendance.date == d).first()
            if existing_att:
                existing_att.check_in_at = cin
                existing_att.check_out_at = cout
                existing_att.check_in = fmt_12h(cin)
                existing_att.check_out = fmt_12h(cout)
                existing_att.working_minutes = calc["working_minutes"]
                existing_att.overtime_minutes = 0
                existing_att.late_minutes = calc["late_minutes"]
                existing_att.final_status = calc["final_status"]

        # 3. Add positive wellbeing survey
        db.add(Survey(
            employee_id=emp2.id, date=today, survey_type="morning", role="employee",
            answers={"stress": 1, "energy": 5, "manageable": 5, "satisfied": 5, "wlb": 5},
            created_at=datetime.utcnow()
        ))
        db.add(Survey(
            employee_id=emp2.id, date=today, survey_type="evening", role="employee",
            answers={"difficulty": 2, "deadline": 1, "overtime": 1, "workload": 2, "completion": 5},
            created_at=datetime.utcnow()
        ))

        # 4. Add positive communication through semantic pipeline
        pos_comm_text = "The project is progressing well, deliverables are on track, and team coordination is going smoothly."
        sem2 = analyze_communication(pos_comm_text)
        db.add(Communication(
            employee_id=emp2.id, text=pos_comm_text, source="reflection",
            sentiment_score=sem2["sentiment_score"], stress_keyword_score=sem2["stress_keyword_score"],
            timestamp=datetime.utcnow()
        ))
        db.commit()

        pred_after_2 = predict_for_employee(db, emp2, persist=True)
        print(f"AFTER:  Score = {pred_after_2['burnout_score']}, Risk = {pred_after_2['risk_level']}, Probabilities = {pred_after_2['probabilities']}")
        assert pred_after_2["burnout_score"] < pred_before_2["burnout_score"], "Prediction score did not decrease after recovery!"
        results["test_2"] = {
            "employee": emp2.name,
            "before_score": pred_before_2["burnout_score"],
            "before_risk": pred_before_2["risk_level"],
            "after_score": pred_after_2["burnout_score"],
            "after_risk": pred_after_2["risk_level"],
            "top_factors": [f["feature"] for f in pred_after_2["risk_factors"][:3]],
            "delta": round(pred_after_2["burnout_score"] - pred_before_2["burnout_score"], 1),
        }

        # -------------------------------------------------------------
        # TEST 3: Neutral Stability Check (Employee: Praveen - Finance)
        # Small routine change does not cause erratic jumps
        # -------------------------------------------------------------
        emp3 = db.query(User).filter(User.email == "praveen@gmail.com").first()
        assert emp3, "Praveen not found"
        print(f"\n--- TEST 3: Routine Stability Check for {emp3.name} ({emp3.email}) ---")

        pred_before_3 = predict_for_employee(db, emp3, persist=False)
        print(f"BEFORE: Score = {pred_before_3['burnout_score']}, Risk = {pred_before_3['risk_level']}")

        # Add routine survey identical to usual profile
        db.add(Survey(
            employee_id=emp3.id, date=today, survey_type="morning", role="employee",
            answers={"stress": 1, "energy": 5, "manageable": 5, "satisfied": 5, "wlb": 5},
            created_at=datetime.utcnow()
        ))
        db.commit()

        pred_after_3 = predict_for_employee(db, emp3, persist=False)
        print(f"AFTER:  Score = {pred_after_3['burnout_score']}, Risk = {pred_after_3['risk_level']}")
        score_diff = abs(pred_after_3["burnout_score"] - pred_before_3["burnout_score"])
        assert score_diff <= 3.0, f"Erratic jump detected! Diff={score_diff}"
        results["test_3"] = {
            "employee": emp3.name,
            "before_score": pred_before_3["burnout_score"],
            "before_risk": pred_before_3["risk_level"],
            "after_score": pred_after_3["burnout_score"],
            "after_risk": pred_after_3["risk_level"],
            "delta": round(score_diff, 1),
        }

        print("\nDYNAMIC BURNOUT TESTS SUMMARY:")
        print(json.dumps(results, indent=2))
        return results

    finally:
        db.close()


def run_ai_assistant_tests():
    print("\n" + "=" * 60)
    print("SECTION 2: AI ASSISTANT VERIFICATION")
    print("=" * 60)
    db = SessionLocal()
    chat_results = []

    try:
        # 1. Employee Queries (Vignesh)
        emp = db.query(User).filter(User.email == "vignesh@gmail.com").first()
        emp_tok = create_token(emp)
        emp_h = {"Authorization": f"Bearer {emp_tok}"}
        emp_queries = [
            "What is my current burnout risk?",
            "Why is my risk high?",
            "How is my workload?",
            "How many tasks are pending?",
            "How was my attendance?",
        ]
        print(f"\n--- AI Chat: Employee Persona ({emp.name}) ---")
        for q in emp_queries:
            resp = client.post("/api/ai/chat", json={"text": q, "pageContext": {"page": "employee_burnout"}}, headers=emp_h)
            assert resp.status_code == 200, f"Chat failed for employee: {resp.text}"
            reply = resp.json()["reply"]
            print(f"Q: '{q}'\nA: {reply[:120]}...\n")
            assert len(reply) > 20, f"Empty reply for '{q}'"
            chat_results.append({"role": "employee", "question": q, "reply_snippet": reply[:100]})

        # 2. Manager Queries (Aakas - Engineering)
        mgr = db.query(User).filter(User.email == "aakas@gmail.com").first()
        mgr_tok = create_token(mgr)
        mgr_h = {"Authorization": f"Bearer {mgr_tok}"}
        mgr_queries = [
            "How is my team doing?",
            "Who has the highest workload?",
            "Which employees need attention?",
            "How many pending tasks does my team have?",
        ]
        print(f"\n--- AI Chat: Manager Persona ({mgr.name}) ---")
        for q in mgr_queries:
            resp = client.post("/api/ai/chat", json={"text": q, "pageContext": {"page": "manager_dashboard"}}, headers=mgr_h)
            assert resp.status_code == 200, f"Chat failed for manager: {resp.text}"
            reply = resp.json()["reply"]
            print(f"Q: '{q}'\nA: {reply[:120]}...\n")
            assert len(reply) > 20, f"Empty reply for '{q}'"
            chat_results.append({"role": "manager", "question": q, "reply_snippet": reply[:100]})

        # 3. HR Queries (Ajai - HR)
        hr = db.query(User).filter(User.email == "ajai@gmail.com").first()
        hr_tok = create_token(hr)
        hr_h = {"Authorization": f"Bearer {hr_tok}"}
        hr_queries = [
            "Which department has the highest workload?",
            "Which employees have high burnout risk?",
            "How is Engineering compared with Finance?",
            "What are the organization wellbeing trends?",
        ]
        print(f"\n--- AI Chat: HR Persona ({hr.name}) ---")
        for q in hr_queries:
            resp = client.post("/api/ai/chat", json={"text": q, "pageContext": {"page": "hr_dashboard"}}, headers=hr_h)
            assert resp.status_code == 200, f"Chat failed for HR: {resp.text}"
            reply = resp.json()["reply"]
            print(f"Q: '{q}'\nA: {reply[:120]}...\n")
            assert len(reply) > 20, f"Empty reply for '{q}'"
            chat_results.append({"role": "hr", "question": q, "reply_snippet": reply[:100]})

        return chat_results

    finally:
        db.close()


def run_api_and_rbac_tests():
    print("\n" + "=" * 60)
    print("SECTION 3: API & RBAC ENDPOINT VERIFICATION")
    print("=" * 60)
    db = SessionLocal()

    try:
        emp = db.query(User).filter(User.email == "vignesh@gmail.com").first()
        mgr = db.query(User).filter(User.email == "aakas@gmail.com").first()
        hr = db.query(User).filter(User.email == "ajai@gmail.com").first()

        emp_tok = create_token(emp)
        mgr_tok = create_token(mgr)
        hr_tok = create_token(hr)

        emp_h = {"Authorization": f"Bearer {emp_tok}"}
        mgr_h = {"Authorization": f"Bearer {mgr_tok}"}
        hr_h = {"Authorization": f"Bearer {hr_tok}"}

        # 1. Employee Dashboard & Endpoints
        r_emp_dash = client.get("/api/employee/dashboard", headers=emp_h)
        assert r_emp_dash.status_code == 200, f"Failed emp dash: {r_emp_dash.text}"
        assert "kpis" in r_emp_dash.json()
        print("PASS: /api/employee/dashboard (200)")

        r_emp_burn = client.get("/api/employee/burnout", headers=emp_h)
        assert r_emp_burn.status_code == 200
        assert "prediction" in r_emp_burn.json()
        print("PASS: /api/employee/burnout (200)")

        r_emp_tasks = client.get("/api/tasks/my", headers=emp_h)
        assert r_emp_tasks.status_code == 200
        print(f"PASS: /api/tasks/my (200, count={len(r_emp_tasks.json().get('tasks', []))})")

        # 2. Manager Dashboard & Endpoints
        r_mgr_dash = client.get("/api/manager/dashboard", headers=mgr_h)
        assert r_mgr_dash.status_code == 200
        print("PASS: /api/manager/dashboard (200)")

        r_mgr_team = client.get("/api/manager/team", headers=mgr_h)
        assert r_mgr_team.status_code == 200
        team = r_mgr_team.json()
        print(f"PASS: /api/manager/team (200, members={len(team)})")
        assert len(team) == 10, f"Expected 10 engineering team members, got {len(team)}"

        r_mgr_workload = client.get("/api/tasks/team", headers=mgr_h)
        assert r_mgr_workload.status_code == 200
        print("PASS: /api/tasks/team (200)")

        # 3. HR Endpoints
        r_hr_dash = client.get("/api/hr/dashboard", headers=hr_h)
        assert r_hr_dash.status_code == 200
        print("PASS: /api/hr/dashboard (200)")

        r_hr_emp = client.get("/api/hr/employees", headers=hr_h)
        assert r_hr_emp.status_code == 200
        all_emps = r_hr_emp.json()
        print(f"PASS: /api/hr/employees (200, total={len(all_emps)})")
        assert len(all_emps) >= 40

        r_hr_depts = client.get("/api/hr/departments", headers=hr_h)
        assert r_hr_depts.status_code == 200
        print("PASS: /api/hr/departments (200)")

        # 4. RBAC Enforcement Checks
        # Employee cannot access manager team endpoint
        r_forbidden_mgr = client.get("/api/manager/team", headers=emp_h)
        assert r_forbidden_mgr.status_code in (401, 403), "RBAC Violation: Employee accessed manager/team!"
        print(f"PASS: RBAC employee accessing /api/manager/team blocked ({r_forbidden_mgr.status_code})")

        # Employee cannot access HR dashboard
        r_forbidden_hr = client.get("/api/hr/dashboard", headers=emp_h)
        assert r_forbidden_hr.status_code in (401, 403), "RBAC Violation: Employee accessed hr/dashboard!"
        print(f"PASS: RBAC employee accessing /api/hr/dashboard blocked ({r_forbidden_hr.status_code})")

        # Manager cannot access HR dashboard
        r_mgr_forbidden_hr = client.get("/api/hr/dashboard", headers=mgr_h)
        assert r_mgr_forbidden_hr.status_code in (401, 403), "RBAC Violation: Manager accessed hr/dashboard!"
        print(f"PASS: RBAC manager accessing /api/hr/dashboard blocked ({r_mgr_forbidden_hr.status_code})")

        print("ALL API & RBAC CHECKS PASSED.")
        return True

    finally:
        db.close()


def count_all_simulation_records():
    print("\n" + "=" * 60)
    print("SECTION 4: DATABASE RECORD TALLY (LIVE SUPABASE POSTGRESQL)")
    print("=" * 60)
    db = SessionLocal()
    try:
        total_users = db.query(User).count()
        depts = db.query(Department).all()
        att_count = db.query(Attendance).count()
        task_count = db.query(Task).count()
        leave_count = db.query(LeaveRequest).count()
        perm_count = db.query(PermissionRequest).count()
        survey_count = db.query(Survey).count()
        pulse_count = db.query(PulseSurvey).count()
        comm_count = db.query(Communication).count()
        pred_count = db.query(Prediction).count()

        # Risk distribution among active predictions
        preds = db.query(Prediction).all()
        risk_dist = {"LOW": 0, "MODERATE": 0, "HIGH": 0}
        for p in preds:
            lvl = p.risk_level or "LOW"
            risk_dist[lvl] = risk_dist.get(lvl, 0) + 1

        summary = {
            "total_users": total_users,
            "departments": [d.name for d in depts],
            "attendance_records": att_count,
            "task_records": task_count,
            "leave_records": leave_count,
            "permission_records": perm_count,
            "survey_records": survey_count,
            "pulse_survey_records": pulse_count,
            "communication_records": comm_count,
            "prediction_records": pred_count,
            "risk_distribution": risk_dist,
        }
        for k, v in summary.items():
            print(f"  {k}: {v}")
        return summary
    finally:
        db.close()


if __name__ == "__main__":
    count_all_simulation_records()
    run_dynamic_burnout_tests()
    run_ai_assistant_tests()
    run_api_and_rbac_tests()
    print("\nALL VERIFICATION MODULES EXECUTED SUCCESSFULLY.")
