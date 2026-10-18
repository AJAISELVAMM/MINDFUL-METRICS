"""
MINDFUL METRICS - Realistic End-to-End Company Simulation Seeder
Populates 45 users (1 HR, 4 Managers, 40 Employees) across 4 Departments
with 60 days of internally consistent attendance, tasks, leaves, permissions,
wellbeing surveys, pulse surveys, communications, and ML burnout predictions.
"""

from __future__ import annotations
import sys
import random
from datetime import date, datetime, time, timedelta
from pathlib import Path

# Add backend root to path
BACKEND_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.database import SessionLocal
from app.models import (
    User, Department, CompanySettings, Attendance, LeaveRequest,
    PermissionRequest, Task, Survey, PulseSurvey, Communication,
    Prediction, BurnoutFeatures
)
from app.security import hash_password
from app.services.attendance_service import get_company_settings, calculate_attendance_rule
from app.services.semantic_service import analyze_communication
from app.services.burnout_service import predict_for_employee, ensure_trained


# ==============================================================
# USER & ORGANIZATION SPECIFICATION
# ==============================================================

HR_DATA = {
    "name": "Ajai",
    "email": "ajai@gmail.com",
    "password": "Ajai@123",
    "role": "hr",
    "department": "HR",
    "employee_code": "H101",
}

MANAGERS_DATA = [
    {
        "name": "Aakas",
        "email": "aakas@gmail.com",
        "password": "Aakas@123",
        "department": "Engineering",
        "employee_code": "M101",
    },
    {
        "name": "Aswin",
        "email": "aswin@gmail.com",
        "password": "Aswin@123",
        "department": "Marketing",
        "employee_code": "M102",
    },
    {
        "name": "Aathi",
        "email": "aathi@gmail.com",
        "password": "Aathi@123",
        "department": "Finance",
        "employee_code": "M103",
    },
    {
        "name": "Divya",
        "email": "divya@gmail.com",
        "password": "Divya@123",
        "department": "Operations",
        "employee_code": "M104",
    },
]

EMPLOYEES_DATA = {
    "Engineering": [
        ("Vignesh", "vignesh@gmail.com", "Vignesh@123", "E201", "low"),
        ("Naveen", "naveen@gmail.com", "Naveen@123", "E202", "low"),
        ("Dinesh", "dinesh@gmail.com", "Dinesh@123", "E203", "low"),
        ("Sathish", "sathish@gmail.com", "Sathish@123", "E204", "low"),
        ("Harish", "harish@gmail.com", "Harish@123", "E205", "moderate"),
        ("Divya", "divya1@gmail.com", "Divya@123", "E206", "moderate"),
        ("Keerthana", "keerthana@gmail.com", "Keerthana@123", "E207", "moderate"),
        ("Swetha", "swetha@gmail.com", "Swetha@123", "E208", "moderate"),
        ("Pavithra", "pavithra@gmail.com", "Pavithra@123", "E209", "high"),
        ("Aishwarya", "aishwarya@gmail.com", "Aishwarya@123", "E210", "high"),
    ],
    "Marketing": [
        ("Sanjay", "sanjay@gmail.com", "Sanjay@123", "E301", "low"),
        ("Madhan", "madhan@gmail.com", "Madhan@123", "E302", "low"),
        ("Surya", "surya@gmail.com", "Surya@123", "E303", "low"),
        ("Ashwin", "ashwin@gmail.com", "Ashwin@123", "E304", "low"),
        ("Manoj", "manoj@gmail.com", "Manoj@123", "E305", "moderate"),
        ("Lakshmi", "lakshmi@gmail.com", "Lakshmi@123", "E306", "moderate"),
        ("Nandhini", "nandhini@gmail.com", "Nandhini@123", "E307", "moderate"),
        ("Harini", "harini@gmail.com", "Harini@123", "E308", "moderate"),
        ("Janani", "janani@gmail.com", "Janani@123", "E309", "high"),
        ("Sangeetha", "sangeetha@gmail.com", "Sangeetha@123", "E310", "high"),
    ],
    "Finance": [
        ("Praveen", "praveen@gmail.com", "Praveen@123", "E401", "low"),
        ("Mohan", "mohan@gmail.com", "Mohan@123", "E402", "low"),
        ("Balaji", "balaji@gmail.com", "Balaji@123", "E403", "low"),
        ("Gokul", "gokul@gmail.com", "Gokul@123", "E404", "low"),
        ("Suresh", "suresh@gmail.com", "Suresh@123", "E405", "moderate"),
        ("Ramya", "ramya@gmail.com", "Ramya@123", "E406", "moderate"),
        ("Deepa", "deepa@gmail.com", "Deepa@123", "E407", "moderate"),
        ("Kavya", "kavya@gmail.com", "Kavya@123", "E408", "moderate"),
        ("Abinaya", "abinaya@gmail.com", "Abinaya@123", "E409", "high"),
        ("Monisha", "monisha@gmail.com", "Monisha@123", "E410", "high"),
    ],
    "Operations": [
        ("Ramesh", "ramesh@gmail.com", "Ramesh@123", "E501", "low"),
        ("Vijay", "vijay@gmail.com", "Vijay@123", "E502", "low"),
        ("Saravanan", "saravanan@gmail.com", "Saravanan@123", "E503", "low"),
        ("Dharani", "dharani@gmail.com", "Dharani@123", "E504", "low"),
        ("Lokesh", "lokesh@gmail.com", "Lokesh@123", "E505", "moderate"),
        ("Sowmya", "sowmya@gmail.com", "Sowmya@123", "E506", "moderate"),
        ("Revathi", "revathi@gmail.com", "Revathi@123", "E507", "moderate"),
        ("Anitha", "anitha@gmail.com", "Anitha@123", "E508", "moderate"),
        ("Shalini", "shalini@gmail.com", "Shalini@123", "E509", "high"),
        ("Mahalakshmi", "mahalakshmi@gmail.com", "Mahalakshmi@123", "E510", "high"),
    ],
}

# Real-world task templates per department
TASK_TEMPLATES = {
    "Engineering": [
        ("Refactor authentication middleware for JWT rotation", "Security improvement for token renewal", 3),
        ("Optimize Postgres connection pooling and indexing", "Database latency optimization and slow query indexing", 4),
        ("Implement automated health check telemetry", "Telemetry endpoints for microservice monitoring", 2),
        ("Fix memory leak in background worker task pool", "Investigate worker lifecycle under heavy queue load", 5),
        ("Migrate legacy REST endpoints to OpenAPI v3", "Documentation and validation standardisation", 3),
        ("Implement end-to-end integration test suites", "Pytest automated integration covering auth and attendance", 3),
        ("Design distributed cache invalidation strategy", "Redis cache synchronization for employee profiles", 4),
        ("Investigate flaky frontend hydration issue", "Debug client render discrepancies in React views", 4),
    ],
    "Marketing": [
        ("Q3 Product Launch Campaign Collateral", "Deliver landing page copy, assets, and sales enablement decks", 3),
        ("Customer Persona Segmentation & Analytics", "Deep-dive into enterprise customer trial retention patterns", 3),
        ("Prepare SEO and Keyword Strategy Report", "Audit competitor ranking terms and content expansion", 2),
        ("Coordinate Webinar Series with Product Team", "Speaker coordination and landing page conversion flow", 3),
        ("Social Media Growth & Engagement Analysis", "Analyze LinkedIn and Twitter campaigns reach metrics", 2),
        ("Brand Identity Guidelines Update", "Refine color palette and digital typography standards", 3),
        ("Conversion Rate Optimization on Landing Page", "A/B test value proposition and call-to-action cards", 4),
        ("Email Marketing Automation Workflow Design", "Lifecycle nurture drip sequence for trial accounts", 4),
    ],
    "Finance": [
        ("Q3 Departmental Budget Variance Analysis", "Analyze actual vs forecast expenditure across business units", 4),
        ("Quarterly Tax Provision & Statutory Compliance", "Verify GST filings and corporate tax accruals", 4),
        ("Audit Accounts Payable & Vendor Invoices", "Reconciliation of outstanding contractor commitments", 3),
        ("Prepare Monthly Cash Flow Forecast Model", "Financial liquidity modeling and sensitivity review", 4),
        ("Capex vs Opex Expenditure Breakdown", "Cloud infrastructure spend categorization audit", 3),
        ("Payroll Reconciliation & Deductions Review", "Statutory benefits, bonuses, and tax deductions sign-off", 3),
        ("Financial Risk & Credit Facility Assessment", "Banking partner risk and credit limits evaluation", 5),
        ("Annual Corporate Financial Reporting Draft", "Balance sheet and P&L audit preparation draft", 5),
    ],
    "Operations": [
        ("Supply Chain Logistics & Vendor SLA Audit", "Audit turnaround times against contracted vendor SLAs", 4),
        ("Office Infrastructure & IT Asset Allocation", "Asset inventory and workstation hardware lifecycle review", 2),
        ("Process Optimization for Internal Helpdesk", "Reduce mean time to resolve tickets from 48h to 12h", 4),
        ("Vendor Contract Renewal Negotiations", "Renegotiate software licensing and hardware leases", 4),
        ("Quarterly Facility Safety & Compliance Audit", "Fire safety, ergonomic standards, and workspace audit", 2),
        ("Standard Operating Procedures (SOP) Overhaul", "Document step-by-step incident response playbook", 3),
        ("Inventory Management System Reconciliation", "Quarterly audit of physical items against database", 3),
        ("Onboarding Operations Workflow Automation", "Automate laptop provisioning and access checklist", 4),
    ],
}

MANAGER_TASKS = [
    ("Q3 Department Performance Reviews & Appraisals", "Complete biannual feedback and roadmap alignment for team", 4),
    ("Cross-Department Resource Planning & Budgeting", "Align headcount growth with organization Q4 goals", 4),
    ("Team Sprint Velocity & Quality Review", "Inspect cycle times, defect escape rate, and blocker bottlenecks", 3),
    ("Workplace Health & Wellbeing Action Plan", "Review team risk metrics and establish balanced scheduling", 3),
    ("Strategic Goal Alignment & OKR Tracking", "Set measurable OKR deliverables and monitor weekly milestones", 4),
]

# Communication messages across stress tiers
COMMUNICATIONS = {
    "low": [
        "The project is progressing well and deliverables are completely on track.",
        "I completed my assigned sprint tickets ahead of schedule today.",
        "The workload is manageable and team coordination is going smoothly.",
        "Great team collaboration during our sprint planning and grooming today.",
        "Clear priorities and well-defined tasks make this week very productive.",
        "Feeling energized and making good headway on the quarterly deliverables.",
        "Everything is running smoothly with no blockers on my desk.",
        "Finished code review and documentation without any delays.",
    ],
    "moderate": [
        "I have several tasks pending this week and deadlines are getting tight.",
        "The deadline is approaching for the upcoming sprint release review.",
        "Workload has increased recently with ad-hoc requests from customers.",
        "Some complex tickets are taking slightly longer than expected to resolve.",
        "Balancing customer escalations and scheduled features is challenging today.",
        "Team coordination is fine, but dependencies are slowing progress down.",
        "A few unexpected tasks were added to my backlog this morning.",
        "Working through dependencies, hoping to wrap up deliverables soon.",
    ],
    "high": [
        "I have been working late for several days and feeling exhausted.",
        "There are too many critical tasks pending and no time to recover.",
        "The deadlines are becoming impossible to manage without weekend work.",
        "I am struggling to keep up with the intense workload and constant blockers.",
        "Constant context switching and urgent escalations are burning me out.",
        "The current workload is becoming difficult to handle without additional help.",
        "Blocked on external reviews and feeling severe pressure regarding due dates.",
        "Working extra hours every day this week, feeling overwhelmed by expectations.",
    ],
}


def fmt_12h(dt: datetime) -> str:
    return dt.strftime("%I:%M %p")


def seed_company_data():
    ensure_trained()
    db = SessionLocal()
    try:
        print(">>> [1/7] Ensuring Company Settings & Departments...")
        settings = get_company_settings(db)
        
        # Ensure required departments
        req_depts = ["Engineering", "Marketing", "Finance", "Operations", "HR"]
        for dname in req_depts:
            dept = db.query(Department).filter(Department.name == dname).first()
            if not dept:
                db.add(Department(name=dname))
        db.commit()

        print(">>> [2/7] Creating/Updating HR & Managers...")
        # 1. HR
        hr_user = db.query(User).filter(User.email == HR_DATA["email"]).first()
        if not hr_user:
            hr_user = User(
                name=HR_DATA["name"],
                email=HR_DATA["email"],
                password_hash=hash_password(HR_DATA["password"]),
                role="hr",
                department=HR_DATA["department"],
                employee_code=HR_DATA["employee_code"],
                manager_name="",
                manager_id=None,
                created_at=datetime.utcnow() - timedelta(days=90),
            )
            db.add(hr_user)
            db.commit()
            db.refresh(hr_user)
        else:
            hr_user.name = HR_DATA["name"]
            hr_user.role = "hr"
            hr_user.password_hash = hash_password(HR_DATA["password"])
            db.commit()

        # 2. Managers
        managers_by_dept: dict[str, User] = {}
        for m_info in MANAGERS_DATA:
            mgr = db.query(User).filter(User.email == m_info["email"]).first()
            if not mgr:
                mgr = User(
                    name=m_info["name"],
                    email=m_info["email"],
                    password_hash=hash_password(m_info["password"]),
                    role="manager",
                    department=m_info["department"],
                    employee_code=m_info["employee_code"],
                    manager_name=hr_user.name,
                    manager_id=hr_user.id,
                    created_at=datetime.utcnow() - timedelta(days=90),
                )
                db.add(mgr)
                db.commit()
                db.refresh(mgr)
            else:
                mgr.name = m_info["name"]
                mgr.role = "manager"
                mgr.department = m_info["department"]
                mgr.password_hash = hash_password(m_info["password"])
                mgr.manager_id = hr_user.id
                mgr.manager_name = hr_user.name
                db.commit()
            managers_by_dept[m_info["department"]] = mgr

            # Link department manager_id
            dept_obj = db.query(Department).filter(Department.name == m_info["department"]).first()
            if dept_obj:
                dept_obj.manager_id = mgr.id
                db.commit()

        print(">>> [3/7] Creating/Updating 40 Employees...")
        employees_by_dept: dict[str, list[tuple[User, str]]] = {d: [] for d in EMPLOYEES_DATA}
        
        for dept_name, emp_list in EMPLOYEES_DATA.items():
            mgr = managers_by_dept[dept_name]
            for name, email, pwd, code, profile in emp_list:
                emp = db.query(User).filter(User.email == email).first()
                if not emp:
                    emp = User(
                        name=name,
                        email=email,
                        password_hash=hash_password(pwd),
                        role="employee",
                        department=dept_name,
                        employee_code=code,
                        manager_name=mgr.name,
                        manager_id=mgr.id,
                        created_at=datetime.utcnow() - timedelta(days=80),
                    )
                    db.add(emp)
                    db.commit()
                    db.refresh(emp)
                else:
                    emp.name = name
                    emp.department = dept_name
                    emp.password_hash = hash_password(pwd)
                    emp.manager_id = mgr.id
                    emp.manager_name = mgr.name
                    db.commit()
                employees_by_dept[dept_name].append((emp, profile))

        print(">>> Total Users in organization verified: 1 HR, 4 Managers, 40 Employees (45 users).")

        # 60 days of historical data
        today = date.today()
        history_days = [today - timedelta(days=i) for i in range(60, -1, -1) if (today - timedelta(days=i)).weekday() < 5]
        print(f">>> [4/7] Generating Relational Attendance, Leaves, Permissions for {len(history_days)} workdays...")

        # Clear existing simulated data for our 45 users only to maintain idempotency
        all_sim_user_ids = [hr_user.id] + [m.id for m in managers_by_dept.values()] + [
            e[0].id for elist in employees_by_dept.values() for e in elist
        ]

        if "--reset-history" in sys.argv:
            print(">>> Resetting historical data for the 45 simulated users...")
            db.query(Attendance).filter(Attendance.employee_id.in_(all_sim_user_ids)).delete(synchronize_session=False)
            db.query(Survey).filter(Survey.employee_id.in_(all_sim_user_ids)).delete(synchronize_session=False)
            db.query(PulseSurvey).filter(PulseSurvey.employee_id.in_(all_sim_user_ids)).delete(synchronize_session=False)
            db.query(Communication).filter(Communication.employee_id.in_(all_sim_user_ids)).delete(synchronize_session=False)
            db.query(LeaveRequest).filter(LeaveRequest.employee_id.in_(all_sim_user_ids)).delete(synchronize_session=False)
            db.query(PermissionRequest).filter(PermissionRequest.employee_id.in_(all_sim_user_ids)).delete(synchronize_session=False)
            db.query(Task).filter(Task.employee_id.in_(all_sim_user_ids)).delete(synchronize_session=False)
            db.query(Prediction).filter(Prediction.employee_id.in_(all_sim_user_ids)).delete(synchronize_session=False)
            db.commit()
            print(">>> Reset complete.")

        # Process each department
        for dept_name, emp_tuples in employees_by_dept.items():
            mgr = managers_by_dept[dept_name]
            print(f"    -> Seeding data for {dept_name} (Manager: {mgr.name}, 10 employees)...")

            # Manager tasks from HR
            existing_mgr_tasks = db.query(Task).filter(Task.employee_id == mgr.id).count()
            if existing_mgr_tasks < len(MANAGER_TASKS):
                for t_name, t_desc, t_diff in MANAGER_TASKS:
                    t = Task(
                        employee_id=mgr.id,
                        assigned_by_id=hr_user.id,
                        assigned_by_name=hr_user.name,
                        name=t_name,
                        description=t_desc,
                        priority="High" if t_diff >= 4 else "Medium",
                        difficulty=t_diff,
                        start_date=today - timedelta(days=40),
                        due_date=today + timedelta(days=15),
                        deadline=(today + timedelta(days=15)).isoformat(),
                        status="In Progress",
                        completion_percentage=65,
                        work_update="Progressing according to executive roadmap milestones.",
                        created_at=datetime.utcnow() - timedelta(days=40),
                    )
                    db.add(t)
                db.commit()

            # Manager attendance
            mgr_existing_att = set(r.date for r in db.query(Attendance.date).filter(Attendance.employee_id == mgr.id).all())
            for d in history_days:
                if d in mgr_existing_att:
                    continue
                cin = datetime.combine(d, time(9, random.choice([5, 10, 15])))
                cout = datetime.combine(d, time(17, random.choice([35, 45, 55])))
                calc = calculate_attendance_rule(settings, cin, cout)
                att = Attendance(
                    employee_id=mgr.id,
                    date=d,
                    check_in=fmt_12h(cin),
                    check_out=fmt_12h(cout),
                    check_in_at=cin,
                    check_out_at=cout,
                    morning_status=calc["morning_status"],
                    afternoon_status=calc["afternoon_status"],
                    final_status=calc["final_status"],
                    working_minutes=calc["working_minutes"],
                    overtime_minutes=calc["overtime_minutes"],
                    late_minutes=calc["late_minutes"],
                    early_checkout_minutes=calc["early_checkout_minutes"],
                    status="Completed",
                )
                db.add(att)
            db.commit()

            # For each employee
            for emp, profile in emp_tuples:
                existing_att_dates = set(r.date for r in db.query(Attendance.date).filter(Attendance.employee_id == emp.id).all())
                
                # 1. Leaves
                existing_leaves = db.query(LeaveRequest).filter(LeaveRequest.employee_id == emp.id).count()
                leave_map: dict[date, LeaveRequest] = {}
                if existing_leaves == 0:
                    # Create 2 realistic leaves over 60 days
                    leave_d1 = history_days[12]
                    l1 = LeaveRequest(
                        employee_id=emp.id,
                        employee_name=emp.name,
                        department=emp.department,
                        role="employee",
                        type="Casual Leave",
                        leave_type="Casual Leave",
                        date=leave_d1.strftime("%d %b %Y"),
                        start_date=leave_d1,
                        end_date=leave_d1,
                        duration="1 day",
                        half_day_session="FULL_DAY",
                        reason="Family event and personal commitments.",
                        status="Approved",
                        manager_status="Approved",
                        approved_by=mgr.name,
                        approver_name=mgr.name,
                        approved_at=datetime.combine(leave_d1 - timedelta(days=2), time(10, 0)),
                        created_at=datetime.combine(leave_d1 - timedelta(days=3), time(9, 30)),
                    )
                    db.add(l1)
                    db.flush()
                    leave_map[leave_d1] = l1

                    # One future pending or past sick leave
                    leave_d2 = history_days[28]
                    l2 = LeaveRequest(
                        employee_id=emp.id,
                        employee_name=emp.name,
                        department=emp.department,
                        role="employee",
                        type="Sick Leave",
                        leave_type="Sick Leave",
                        date=leave_d2.strftime("%d %b %Y"),
                        start_date=leave_d2,
                        end_date=leave_d2,
                        duration="0.5 day",
                        half_day_session="MORNING_HALF_DAY",
                        reason="Doctor medical appointment in the morning.",
                        status="Approved",
                        manager_status="Approved",
                        approved_by=mgr.name,
                        approver_name=mgr.name,
                        approved_at=datetime.combine(leave_d2 - timedelta(days=1), time(16, 0)),
                        created_at=datetime.combine(leave_d2 - timedelta(days=1), time(14, 0)),
                    )
                    db.add(l2)
                    db.flush()
                    leave_map[leave_d2] = l2

                # 2. Permissions
                existing_perms = db.query(PermissionRequest).filter(PermissionRequest.employee_id == emp.id).count()
                perm_map: dict[date, PermissionRequest] = {}
                if existing_perms == 0:
                    perm_d = history_days[20]
                    p1 = PermissionRequest(
                        employee_id=emp.id,
                        employee_name=emp.name,
                        department=emp.department,
                        role="employee",
                        date=perm_d,
                        requested_checkout_time="04:30 PM",
                        reason="Personal errand requiring early departure.",
                        status="Approved",
                        approved_by=mgr.name,
                        approver_name=mgr.name,
                        approved_at=datetime.combine(perm_d, time(11, 0)),
                        created_at=datetime.combine(perm_d, time(9, 15)),
                    )
                    db.add(p1)
                    db.flush()
                    perm_map[perm_d] = p1

                # 3. Attendance across history_days using calculate_attendance_rule
                for d in history_days:
                    if d in existing_att_dates:
                        continue
                    
                    app_leave = leave_map.get(d)
                    app_perm = perm_map.get(d)

                    if app_leave and app_leave.half_day_session == "FULL_DAY":
                        calc = calculate_attendance_rule(settings, None, None, approved_leave=app_leave)
                        att = Attendance(
                            employee_id=emp.id,
                            date=d,
                            check_in=None,
                            check_out=None,
                            morning_status=calc["morning_status"],
                            afternoon_status=calc["afternoon_status"],
                            final_status=calc["final_status"],
                            working_minutes=0,
                            overtime_minutes=0,
                            late_minutes=0,
                            early_checkout_minutes=0,
                            approved_leave_id=app_leave.id,
                            status="Leave",
                        )
                        db.add(att)
                    elif app_leave and app_leave.half_day_session == "MORNING_HALF_DAY":
                        cin = datetime.combine(d, time(13, 0))
                        cout = datetime.combine(d, time(17, 30))
                        calc = calculate_attendance_rule(settings, cin, cout, approved_leave=app_leave)
                        att = Attendance(
                            employee_id=emp.id,
                            date=d,
                            check_in=fmt_12h(cin),
                            check_out=fmt_12h(cout),
                            check_in_at=cin,
                            check_out_at=cout,
                            morning_status=calc["morning_status"],
                            afternoon_status=calc["afternoon_status"],
                            final_status=calc["final_status"],
                            working_minutes=calc["working_minutes"],
                            overtime_minutes=calc["overtime_minutes"],
                            late_minutes=calc["late_minutes"],
                            early_checkout_minutes=calc["early_checkout_minutes"],
                            approved_leave_id=app_leave.id,
                            status="Completed",
                        )
                        db.add(att)
                    elif app_perm:
                        cin = datetime.combine(d, time(9, 10))
                        cout = datetime.combine(d, time(16, 30))
                        calc = calculate_attendance_rule(settings, cin, cout, approved_permission=app_perm)
                        att = Attendance(
                            employee_id=emp.id,
                            date=d,
                            check_in=fmt_12h(cin),
                            check_out=fmt_12h(cout),
                            check_in_at=cin,
                            check_out_at=cout,
                            morning_status=calc["morning_status"],
                            afternoon_status=calc["afternoon_status"],
                            final_status=calc["final_status"],
                            working_minutes=calc["working_minutes"],
                            overtime_minutes=calc["overtime_minutes"],
                            late_minutes=calc["late_minutes"],
                            early_checkout_minutes=calc["early_checkout_minutes"],
                            approved_permission_id=app_perm.id,
                            status="Completed",
                        )
                        db.add(att)
                    else:
                        # Normal day governed by profile
                        if profile == "low":
                            cin = datetime.combine(d, time(9, random.choice([5, 10, 15, 20])))
                            cout = datetime.combine(d, time(17, random.choice([15, 20, 25, 30])))
                        elif profile == "moderate":
                            is_late = random.random() < 0.2
                            cin_m = random.choice([35, 42]) if is_late else random.choice([15, 25])
                            cin = datetime.combine(d, time(9, cin_m))
                            # Checkout with moderate overtime (18:00 to 18:35, 30-65 mins OT)
                            cout = datetime.combine(d, time(18, random.choice([5, 15, 25, 35])))
                        else:  # high risk profile: heavy overtime
                            is_tired_late = random.random() < 0.2
                            cin_m = random.choice([35, 42]) if is_tired_late else random.choice([10, 20])
                            cin = datetime.combine(d, time(9, cin_m))
                            # Checkout late in evening (18:45 to 20:00)
                            cout_h = random.choice([18, 19, 19])
                            cout_m = random.choice([15, 30, 45, 50])
                            cout = datetime.combine(d, time(cout_h, cout_m))

                        calc = calculate_attendance_rule(settings, cin, cout)
                        att = Attendance(
                            employee_id=emp.id,
                            date=d,
                            check_in=fmt_12h(cin),
                            check_out=fmt_12h(cout),
                            check_in_at=cin,
                            check_out_at=cout,
                            morning_status=calc["morning_status"],
                            afternoon_status=calc["afternoon_status"],
                            final_status=calc["final_status"],
                            working_minutes=calc["working_minutes"],
                            overtime_minutes=calc["overtime_minutes"],
                            late_minutes=calc["late_minutes"],
                            early_checkout_minutes=calc["early_checkout_minutes"],
                            status="Completed",
                        )
                        db.add(att)

                # 4. Tasks (5-8 tasks per employee)
                existing_tasks = db.query(Task).filter(Task.employee_id == emp.id).count()
                if existing_tasks == 0:
                    tpls = TASK_TEMPLATES[dept_name]
                    num_tasks = 6 if profile == "low" else (8 if profile == "moderate" else 9)
                    for t_idx in range(min(num_tasks, len(tpls))):
                        t_name, t_desc, base_diff = tpls[t_idx]
                        if profile == "low":
                            diff = max(1, base_diff - 1)
                            st = "Completed" if t_idx < 5 else "In Progress"
                            prog = 100 if st == "Completed" else 75
                            update_txt = "Completed unit tests and refactored core database handlers."
                            blocker = None
                        elif profile == "moderate":
                            diff = base_diff
                            st = "Completed" if t_idx < 4 else ("In Progress" if t_idx < 7 else "Not Started")
                            prog = 100 if st == "Completed" else (50 if st == "In Progress" else 0)
                            update_txt = "Working on module integration and resolving edge case bugs."
                            blocker = None
                        else:  # high profile
                            diff = min(5, base_diff + 1)
                            if t_idx < 2:
                                st, prog = "Completed", 100
                                blocker = None
                            elif t_idx < 6:
                                st, prog = "In Progress", 35
                                blocker = None
                            else:
                                st, prog = "Blocked", 25
                                blocker = "Blocked on upstream API latency and pending security audit approvals."
                            update_txt = "Struggling with complex dependency issues and unexpected performance bottlenecks."

                        task_obj = Task(
                            employee_id=emp.id,
                            assigned_by_id=mgr.id,
                            assigned_by_name=mgr.name,
                            name=t_name,
                            description=t_desc,
                            priority="High" if diff >= 4 else ("Medium" if diff == 3 else "Low"),
                            difficulty=diff,
                            start_date=today - timedelta(days=35 - t_idx * 3),
                            due_date=today + timedelta(days=7 + t_idx * 2) if st != "Completed" else today - timedelta(days=2),
                            deadline=(today + timedelta(days=7 + t_idx * 2)).isoformat(),
                            status=st,
                            completion_percentage=prog,
                            work_update=update_txt,
                            blocked_reason=blocker,
                            completed_at=datetime.utcnow() - timedelta(days=5) if st == "Completed" else None,
                            created_at=datetime.utcnow() - timedelta(days=35 - t_idx * 3),
                        )
                        db.add(task_obj)

                # 5. Wellbeing Surveys (morning & evening across recent 14 days)
                existing_surveys = db.query(Survey).filter(Survey.employee_id == emp.id).count()
                if existing_surveys < 10:
                    for s_day in history_days[-10:]:
                        if profile == "low":
                            m_ans = {"stress": 1, "energy": 5, "manageable": 5, "satisfied": 5, "wlb": 5}
                            e_ans = {"difficulty": 2, "deadline": 1, "overtime": 1, "workload": 2, "completion": 5}
                        elif profile == "moderate":
                            m_ans = {"stress": 4, "energy": 3, "manageable": 2, "satisfied": 3, "wlb": 2}
                            e_ans = {"difficulty": 4, "deadline": 4, "overtime": 3, "workload": 4, "completion": 3}
                        else:  # high profile
                            m_ans = {"stress": 5, "energy": 1, "manageable": 1, "satisfied": 2, "wlb": 1}
                            e_ans = {"difficulty": 5, "deadline": 5, "overtime": 5, "workload": 5, "completion": 2}

                        # Morning check-in
                        db.add(Survey(
                            employee_id=emp.id,
                            date=s_day,
                            survey_type="morning",
                            role="employee",
                            answers=m_ans,
                            note=None,
                            created_at=datetime.combine(s_day, time(9, 30)),
                        ))
                        # Evening check-in
                        db.add(Survey(
                            employee_id=emp.id,
                            date=s_day,
                            survey_type="evening",
                            role="employee",
                            answers=e_ans,
                            note=None,
                            created_at=datetime.combine(s_day, time(17, 15)),
                        ))

                # 6. Pulse Surveys
                existing_pulse = db.query(PulseSurvey).filter(PulseSurvey.employee_id == emp.id).count()
                if existing_pulse == 0:
                    resp_val = "Low" if profile == "low" else ("Moderate" if profile == "moderate" else "Very High")
                    db.add(PulseSurvey(
                        employee_id=emp.id,
                        date=today,
                        workload_response=resp_val,
                        created_at=datetime.utcnow(),
                    ))

                # 7. Communications via Semantic Pipeline
                existing_comms = db.query(Communication).filter(Communication.employee_id == emp.id).count()
                if existing_comms < 5:
                    texts = COMMUNICATIONS[profile]
                    for c_idx, txt in enumerate(texts[:5]):
                        sem = analyze_communication(txt)
                        db.add(Communication(
                            employee_id=emp.id,
                            text=txt,
                            source="reflection",
                            sentiment_score=sem.get("sentiment_score", 0.0),
                            stress_keyword_score=sem.get("stress_keyword_score", 0.0),
                            timestamp=datetime.utcnow() - timedelta(days=c_idx * 3),
                        ))

            # Commit batch for this department
            db.commit()

        print(">>> [5/7] Executing Machine Learning Burnout Predictions for all 40 employees...")
        predictions_summary = {"LOW": 0, "MODERATE": 0, "HIGH": 0}
        emp_scores = []

        for dept_name, emp_tuples in employees_by_dept.items():
            for emp, expected_tier in emp_tuples:
                pred = predict_for_employee(db, emp, persist=True)
                score = pred.get("burnout_score", 0)
                tier = pred.get("risk_level", "LOW")
                predictions_summary[tier] = predictions_summary.get(tier, 0) + 1
                emp_scores.append((emp.name, dept_name, score, tier, expected_tier))

        # Also execute ML burnout predictions for all managers
        for dept_name, mgr in managers_by_dept.items():
            pred = predict_for_employee(db, mgr, persist=True)
            score = pred.get("burnout_score", 0)
            tier = pred.get("risk_level", "LOW")
            predictions_summary[tier] = predictions_summary.get(tier, 0) + 1
            emp_scores.append((mgr.name, dept_name, score, tier, "Manager (Normal)"))

        db.commit()
        print(f">>> [6/7] Machine Learning Predictions Completed:")
        print(f"    Total Evaluated: {len(emp_scores)} users ({len(managers_by_dept)} managers + {len(emp_scores) - len(managers_by_dept)} employees)")
        print(f"    Risk Distribution: LOW: {predictions_summary.get('LOW')}, MODERATE: {predictions_summary.get('MODERATE')}, HIGH: {predictions_summary.get('HIGH')}")

        print(">>> Sample employee predictions:")
        for name, dept, score, tier, exp_tier in emp_scores[:8]:
            print(f"    * {name} ({dept}): Score={score:.1f}, Risk={tier} (Expected Profile: {exp_tier})")

        return {
            "hr": hr_user,
            "managers": managers_by_dept,
            "employees": employees_by_dept,
            "predictions_summary": predictions_summary,
            "emp_scores": emp_scores,
        }
    finally:
        db.close()


if __name__ == "__main__":
    seed_company_data()
