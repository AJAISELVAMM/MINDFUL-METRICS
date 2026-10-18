from __future__ import annotations
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from .models import (
    User, Department, CompanySettings, Attendance, LeaveRequest,
    PermissionRequest, Task, Notification, Communication, Survey,
    PulseSurvey, Prediction
)
from .security import hash_password
from .services.burnout_service import predict_for_employee


USERS_DATA = [
    ("Arjun Mehta", "employee@gmail.com", "employee", "Engineering", "E118", "Priya Nair"),
    ("Priya Nair", "manager@gmail.com", "manager", "Engineering", "M001", "HR Team"),
    ("HR Team", "hr@gmail.com", "hr", "HR", "H001", ""),
    ("Rahul Sharma", "rahul.sharma@gmail.com", "employee", "Engineering", "E102", "Priya Nair"),
    ("Anita Krishnan", "anita.krishnan@gmail.com", "employee", "Engineering", "E109", "Priya Nair"),
    ("Vikram Rao", "vikram.rao@gmail.com", "employee", "Engineering", "E121", "Priya Nair"),
    ("Sneha Reddy", "sneha.reddy@gmail.com", "employee", "Testing", "E130", "Priya Nair"),
    ("Deepak Verma", "deepak.verma@gmail.com", "employee", "Design", "E145", "Priya Nair"),
    ("Kavita Shah", "kavita.shah@gmail.com", "employee", "Support", "E152", "Priya Nair"),
]

DEPARTMENTS = ["Engineering", "Testing", "Design", "Support", "HR", "Sales"]


def seed(db: Session):
    # Ensure Company Settings
    if not db.query(CompanySettings).first():
        db.add(CompanySettings(
            work_start_time="09:00",
            checkin_grace_time="09:30",
            afternoon_start_time="13:00",
            early_checkout_threshold="17:00",
            work_end_time="17:30",
            timezone="Asia/Kolkata",
            survey_start_time="11:30",
            survey_end_time="15:00",
        ))

    # Ensure Departments
    for d_name in DEPARTMENTS:
        if not db.query(Department).filter(Department.name == d_name).first():
            db.add(Department(name=d_name))

    # Ensure 2026 Tamil Nadu Government Public Holidays
    try:
        from .services.holiday_service import seed_2026_holidays
        seed_2026_holidays(db)
    except Exception as e:
        print("[SEED WARNING] Could not seed holidays:", e)

    # Create users if none exist
    if not db.query(User).first():
        pw = hash_password("demo123")
        created_users = {}
        for name, email, role, dept, code, mgr in USERS_DATA:
            u = User(
                name=name,
                email=email,
                password_hash=pw,
                role=role,
                department=dept,
                employee_code=code,
                manager_name=mgr,
                created_at=datetime.utcnow() - timedelta(days=60),
            )
            db.add(u)
            created_users[code] = u
        db.flush()

        # Update manager_id relations
        priya = created_users.get("M001")
        hr = created_users.get("H001")
        if priya:
            for code, u in created_users.items():
                if code not in ("M001", "H001"):
                    u.manager_id = priya.id
            priya.manager_id = hr.id if hr else None
        db.flush()

        today = date.today()

        # Seed attendance for Arjun Mehta (Employee)
        arjun = created_users["E118"]
        for i in range(14, 0, -1):
            d = today - timedelta(days=i)
            if d.weekday() >= 5:
                continue
            # vary attendance times
            if i % 5 == 0:
                # 09:35 Checkin -> MORNING_HALF_DAY_ABSENT
                check_in_dt = datetime.combine(d, datetime.strptime("09:35 AM", "%I:%M %p").time())
                check_out_dt = datetime.combine(d, datetime.strptime("05:15 PM", "%I:%M %p").time())
                db.add(Attendance(
                    employee_id=arjun.id, date=d, check_in="09:35 AM", check_out="05:15 PM",
                    check_in_at=check_in_dt, check_out_at=check_out_dt,
                    morning_status="MORNING_HALF_DAY_ABSENT", afternoon_status="PRESENT",
                    final_status="MORNING_HALF_DAY_ABSENT",
                    working_minutes=460, overtime_minutes=0, late_minutes=35, early_checkout_minutes=0,
                    status="Completed",
                ))
            else:
                # Standard checkin with slight overtime
                check_in_dt = datetime.combine(d, datetime.strptime("09:10 AM", "%I:%M %p").time())
                check_out_dt = datetime.combine(d, datetime.strptime("06:15 PM", "%I:%M %p").time())
                db.add(Attendance(
                    employee_id=arjun.id, date=d, check_in="09:10 AM", check_out="06:15 PM",
                    check_in_at=check_in_dt, check_out_at=check_out_dt,
                    morning_status="PRESENT", afternoon_status="PRESENT",
                    final_status="FULL_DAY_PRESENT",
                    working_minutes=545, overtime_minutes=45, late_minutes=10, early_checkout_minutes=0,
                    status="Completed",
                ))

        # Seed attendance for Priya Nair (Manager is ALSO an employee!)
        if priya:
            for i in range(14, 0, -1):
                d = today - timedelta(days=i)
                if d.weekday() >= 5:
                    continue
                check_in_dt = datetime.combine(d, datetime.strptime("09:05 AM", "%I:%M %p").time())
                check_out_dt = datetime.combine(d, datetime.strptime("06:00 PM", "%I:%M %p").time())
                db.add(Attendance(
                    employee_id=priya.id, date=d, check_in="09:05 AM", check_out="06:00 PM",
                    check_in_at=check_in_dt, check_out_at=check_out_dt,
                    morning_status="PRESENT", afternoon_status="PRESENT",
                    final_status="FULL_DAY_PRESENT",
                    working_minutes=535, overtime_minutes=30, late_minutes=5, early_checkout_minutes=0,
                    status="Completed",
                ))

        # Seed attendance for other team members
        other_codes = ["E102", "E109", "E121", "E130", "E145", "E152"]
        for code in other_codes:
            u = created_users.get(code)
            if not u:
                continue
            for i in range(7, 0, -1):
                d = today - timedelta(days=i)
                if d.weekday() >= 5:
                    continue
                check_in_dt = datetime.combine(d, datetime.strptime("09:12 AM", "%I:%M %p").time())
                check_out_dt = datetime.combine(d, datetime.strptime("05:30 PM", "%I:%M %p").time())
                db.add(Attendance(
                    employee_id=u.id, date=d, check_in="09:12 AM", check_out="05:30 PM",
                    check_in_at=check_in_dt, check_out_at=check_out_dt,
                    morning_status="PRESENT", afternoon_status="PRESENT",
                    final_status="FULL_DAY_PRESENT",
                    working_minutes=498, overtime_minutes=0, late_minutes=12, early_checkout_minutes=0,
                    status="Completed",
                ))

        # Seed Tasks
        tasks_data = [
            (arjun.id, "Sprint 24 API contract review", "Complete schema mapping for new backend routes", "High", "Today", "In Progress", 4, 60),
            (arjun.id, "Auth session timeout fix", "Resolve edge cases in JWT refresh tokens", "High", "Tomorrow", "Pending", 3, 20),
            (arjun.id, "Dashboard KPI widget polish", "Integrate real backend endpoints to dashboard cards", "Medium", "15 Oct", "In Progress", 2, 50),
            (arjun.id, "Leave calendar edge cases", "Support morning and afternoon half-day leaves", "Medium", "18 Oct", "Completed", 3, 100),
            (arjun.id, "Notification digest emails", "Aggregate daily alerts into morning summary", "Medium", "04 Oct", "Overdue", 3, 0),
        ]
        if priya:
            tasks_data.extend([
                (priya.id, "Quarterly Engineering Capacity Plan", "Review team velocity and allocation for Q4", "High", "12 Oct", "In Progress", 4, 40),
                (priya.id, "Architecture Sync: Microservices Migration", "Finalize API gateway contracts", "Medium", "15 Oct", "Pending", 3, 0),
                (priya.id, "Team Wellbeing & Workload Retrospective", "Hold monthly workload distribution session", "High", "Today", "Completed", 2, 100),
            ])
        for emp_id, name, desc, prio, dead, stat, diff, pct in tasks_data:
            db.add(Task(
                employee_id=emp_id, name=name, description=desc, priority=prio,
                deadline=dead, status=stat, difficulty=diff, completion_percentage=pct,
            ))

        # Seed Leaves
        rahul = created_users.get("E102")
        anita = created_users.get("E109")
        db.add(LeaveRequest(
            employee_id=arjun.id, employee_name=arjun.name, department="Engineering", role="employee",
            type="Casual Leave", leave_type="Casual Leave", date="18 Sep 2026",
            start_date=today - timedelta(days=12), end_date=today - timedelta(days=12),
            duration="1 day", half_day_session="FULL_DAY", reason="Family function",
            status="Approved", manager_status="Approved", approved_by="Priya Nair", approver_name="Priya Nair",
            approved_at=datetime.utcnow() - timedelta(days=13),
        ))
        if rahul:
            db.add(LeaveRequest(
                employee_id=rahul.id, employee_name=rahul.name, department="Engineering", role="employee",
                type="Casual Leave", leave_type="Casual Leave", date="25 Oct 2026",
                start_date=today + timedelta(days=5), end_date=today + timedelta(days=6),
                duration="2 days", half_day_session="FULL_DAY", reason="Personal work and travel",
                status="Pending", manager_status="Pending",
            ))
        if anita:
            db.add(LeaveRequest(
                employee_id=anita.id, employee_name=anita.name, department="Engineering", role="employee",
                type="Sick Leave", leave_type="Sick Leave", date="14 Sep 2026",
                start_date=today - timedelta(days=16), end_date=today - timedelta(days=16),
                duration="0.5 day", half_day_session="MORNING_HALF_DAY", reason="Dental appointment",
                status="Approved", manager_status="Approved", approved_by="Priya Nair", approver_name="Priya Nair",
                approved_at=datetime.utcnow() - timedelta(days=17),
            ))
        if priya:
            # Manager's OWN leave request (routes to HR!)
            db.add(LeaveRequest(
                employee_id=priya.id, employee_name=priya.name, department="Engineering", role="manager",
                type="Earned Leave", leave_type="Earned Leave", date="28 Oct 2026",
                start_date=today + timedelta(days=8), end_date=today + timedelta(days=9),
                duration="2 days", half_day_session="FULL_DAY", reason="Annual family leave",
                status="Pending", manager_status="Pending",
            ))

        # Seed Permissions
        db.add(PermissionRequest(
            employee_id=arjun.id, employee_name=arjun.name, department="Engineering", role="employee",
            date=today - timedelta(days=3), requested_checkout_time="04:30 PM",
            reason="Doctor consultation", status="Approved", approved_by="Priya Nair",
            approver_name="Priya Nair", approved_at=datetime.utcnow() - timedelta(days=3),
        ))
        if rahul:
            db.add(PermissionRequest(
                employee_id=rahul.id, employee_name=rahul.name, department="Engineering", role="employee",
                date=today, requested_checkout_time="04:00 PM",
                reason="Bank work requiring physical presence", status="Pending",
            ))
        if priya:
            db.add(PermissionRequest(
                employee_id=priya.id, employee_name=priya.name, department="Engineering", role="manager",
                date=today - timedelta(days=1), requested_checkout_time="04:30 PM",
                reason="Conference registration and setup", status="Approved",
                approved_by="HR Team", approver_name="HR Team", approved_at=datetime.utcnow() - timedelta(days=1),
            ))

        # Seed Communications & Surveys
        sample_comm = "Feeling pressure with multiple sprint deadlines and extended evening hours."
        db.add(Communication(employee_id=arjun.id, text=sample_comm, sentiment_score=-0.35, stress_keyword_score=0.6))
        db.add(Survey(
            employee_id=arjun.id, date=today, survey_type="morning", role="employee",
            answers={
                "stress": 4, "energy": 2, "mood": 3, "focus": 3, "wlb": 2,
                "manageable": 2, "deadline": 4, "difficulty": 4, "blockers": 3, "overtime": 4,
            },
        ))
        db.add(PulseSurvey(employee_id=arjun.id, date=today, workload_response="High"))

        if priya:
            db.add(Survey(
                employee_id=priya.id, date=today, survey_type="manager", role="manager",
                answers={
                    "team_workload": 3, "meeting_load": 4, "team_support": 4, "escalations": 2,
                    "coordination": 3, "unexpected_mgmt": 3, "personal_workload": 3, "overtime_mgmt": 3,
                },
            ))

        # Notifications
        db.add(Notification(employee_id=arjun.id, title="Daily Wellbeing Check-in", body="Daily wellbeing survey is available during work hours.", time="Now", unread=1))
        db.add(Notification(employee_id=arjun.id, title="Permission Approved", body="Your permission request for 04:30 PM checkout was approved.", time="2d ago", unread=0))
        if priya:
            db.add(Notification(employee_id=priya.id, title="Pending Team Leave Request", body="Rahul Sharma submitted a Casual Leave request.", time="1h ago", unread=1))
            db.add(Notification(employee_id=priya.id, title="Early Checkout Permission", body="Rahul Sharma requested early checkout at 04:00 PM.", time="3h ago", unread=1))

        db.commit()

        # Generate initial burnout predictions
        for u in created_users.values():
            try:
                predict_for_employee(db, u, persist=True)
            except Exception:
                pass
        db.commit()
