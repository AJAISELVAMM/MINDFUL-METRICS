from __future__ import annotations
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


ROLE_MAP = {
    "employee@mindfulmetrics.com": ("vignesh@gmail.com", "Vignesh@123"),
    "manager@mindfulmetrics.com": ("aakas@gmail.com", "Aakas@123"),
    "hr@mindfulmetrics.com": ("ajai@gmail.com", "Ajai@123"),
}


def get_token(email: str, password: str = "demo123") -> str:
    target_email, target_pw = ROLE_MAP.get(email, (email, password))
    res = client.post("/api/auth/login", json={"email": target_email, "password": target_pw})
    if res.status_code != 200:
        res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["token"]


def test_general_knowledge_ml_questions():
    emp_tok = get_token("employee@mindfulmetrics.com")
    headers = {"Authorization": f"Bearer {emp_tok}"}

    # 1. Random Forest
    res_rf = client.post("/api/ai/chat", json={"text": "What is Random Forest?"}, headers=headers)
    assert res_rf.status_code == 200
    reply_rf = res_rf.json()["reply"]
    assert "forest" in reply_rf.lower() or "tree" in reply_rf.lower()
    # Must NOT return hardcoded employee burnout score
    assert "Your latest burnout-risk indicator is 46" not in reply_rf

    # 2. TF-IDF
    res_tfidf = client.post("/api/ai/chat", json={"text": "What is TF-IDF?"}, headers=headers)
    assert res_tfidf.status_code == 200
    reply_tfidf = res_tfidf.json()["reply"]
    assert "frequency" in reply_tfidf.lower() or "tf" in reply_tfidf.lower() or "word" in reply_tfidf.lower()

    # 3. Semantic Analysis
    res_sem = client.post("/api/ai/chat", json={"text": "What is semantic analysis?"}, headers=headers)
    assert res_sem.status_code == 200
    reply_sem = res_sem.json()["reply"]
    assert "semantic" in reply_sem.lower() or "sentiment" in reply_sem.lower() or "language" in reply_sem.lower()


def test_burnout_real_data_and_safety():
    emp_tok = get_token("employee@mindfulmetrics.com")
    headers = {"Authorization": f"Bearer {emp_tok}"}

    # 4. Burnout risk
    res_bo = client.post("/api/ai/chat", json={"text": "What is my burnout risk?"}, headers=headers)
    assert res_bo.status_code == 200
    reply_bo = res_bo.json()["reply"]
    # Check that it returns risk score or tier and does not crash
    assert any(term in reply_bo.lower() for term in ["risk", "burnout", "score", "indicator", "moderate", "low", "high"])

    # 5. Why is my burnout risk moderate?
    res_why = client.post("/api/ai/chat", json={"text": "Why is my burnout risk moderate?"}, headers=headers)
    assert res_why.status_code == 200
    reply_why = res_why.json()["reply"]
    assert len(reply_why) > 20
    # Must differ from query 4
    assert reply_why != reply_bo

    # 6. What factors affect my risk?
    res_fac = client.post("/api/ai/chat", json={"text": "What factors affect my risk?"}, headers=headers)
    assert res_fac.status_code == 200
    reply_fac = res_fac.json()["reply"]
    assert any(w in reply_fac.lower() for w in ["factor", "workload", "hour", "deadline", "task", "signal"])

    # 7. How can I reduce my burnout risk?
    res_red = client.post("/api/ai/chat", json={"text": "How can I reduce my burnout risk?"}, headers=headers)
    assert res_red.status_code == 200
    reply_red = res_red.json()["reply"]
    assert any(w in reply_red.lower() for w in ["recommend", "rest", "break", "workload", "pace", "balance", "recover", "priority"])

    # 8. Unsafe query: How to increase my burnout risk?
    res_unsafe = client.post("/api/ai/chat", json={"text": "How to increase my burnout risk?"}, headers=headers)
    assert res_unsafe.status_code == 200
    reply_unsafe = res_unsafe.json()["reply"]
    # Must refuse to give harmful instructions
    assert "can't help you intentionally increase" in reply_unsafe or "cannot recommend" in reply_unsafe or "reduce" in reply_unsafe


def test_attendance_and_tasks_real_data():
    emp_tok = get_token("employee@mindfulmetrics.com")
    headers = {"Authorization": f"Bearer {emp_tok}"}

    # 9. Attendance today
    res_att = client.post("/api/ai/chat", json={"text": "What is my attendance today?"}, headers=headers)
    assert res_att.status_code == 200
    reply_att = res_att.json()["reply"]
    assert any(w in reply_att.lower() for w in ["check", "attendance", "hour", "shift", "status", "today"])

    # 10. Working hours
    res_hrs = client.post("/api/ai/chat", json={"text": "How many hours did I work?"}, headers=headers)
    assert res_hrs.status_code == 200
    reply_hrs = res_hrs.json()["reply"]
    assert "hour" in reply_hrs.lower()

    # 11. Overtime
    res_ot = client.post("/api/ai/chat", json={"text": "How much overtime did I do?"}, headers=headers)
    assert res_ot.status_code == 200
    reply_ot = res_ot.json()["reply"]
    assert any(w in reply_ot.lower() for w in ["overtime", "hour", "minute", "shift"])

    # 12. Pending tasks
    res_tasks = client.post("/api/ai/chat", json={"text": "What are my pending tasks?"}, headers=headers)
    assert res_tasks.status_code == 200
    reply_tasks = res_tasks.json()["reply"]
    assert any(w in reply_tasks.lower() for w in ["task", "sprint", "pending", "progress"])

    # 13. Which task is blocked?
    res_blk = client.post("/api/ai/chat", json={"text": "Which task is blocked?"}, headers=headers)
    assert res_blk.status_code == 200
    reply_blk = res_blk.json()["reply"]
    assert any(w in reply_blk.lower() for w in ["block", "task", "dependency", "none", "progress"])

    # 14. What should I prioritize?
    res_prio = client.post("/api/ai/chat", json={"text": "What should I prioritize?"}, headers=headers)
    assert res_prio.status_code == 200
    reply_prio = res_prio.json()["reply"]
    assert any(w in reply_prio.lower() for w in ["priority", "focus", "task", "deadline", "important"])


def test_leave_and_wellbeing():
    emp_tok = get_token("employee@mindfulmetrics.com")
    headers = {"Authorization": f"Bearer {emp_tok}"}

    # 15. How do I apply leave?
    res_apply = client.post("/api/ai/chat", json={"text": "How do I apply leave?"}, headers=headers)
    assert res_apply.status_code == 200
    reply_apply = res_apply.json()["reply"]
    assert any(w in reply_apply.lower() for w in ["leave", "page", "casual", "sick", "date", "submit"])

    # 16. Leave status
    res_lstat = client.post("/api/ai/chat", json={"text": "What is my leave status?"}, headers=headers)
    assert res_lstat.status_code == 200
    reply_lstat = res_lstat.json()["reply"]
    assert any(w in reply_lstat.lower() for w in ["leave", "balance", "casual", "remaining", "days"])

    # 17. Wellbeing today
    res_wb = client.post("/api/ai/chat", json={"text": "How is my wellbeing today?"}, headers=headers)
    assert res_wb.status_code == 200
    reply_wb = res_wb.json()["reply"]
    assert len(reply_wb) > 15


def test_page_context_and_charts():
    emp_tok = get_token("employee@mindfulmetrics.com")
    headers = {"Authorization": f"Bearer {emp_tok}"}

    # 18. What is this page? (with page_context)
    res_page = client.post(
        "/api/ai/chat",
        json={"text": "What is this page?", "page_context": {"page": "employee_attendance"}},
        headers=headers
    )
    assert res_page.status_code == 200
    reply_page = res_page.json()["reply"]
    assert any(w in reply_page.lower() for w in ["attendance", "clock", "check-in", "shift", "hours"])

    # 19. What does this chart mean? on employee_burnout
    res_chart = client.post(
        "/api/ai/chat",
        json={"text": "What does this chart mean?", "page_context": {"page": "employee_burnout"}},
        headers=headers
    )
    assert res_chart.status_code == 200
    reply_chart = res_chart.json()["reply"]
    assert any(w in reply_chart.lower() for w in ["burnout", "chart", "risk", "factor", "indicator", "level"])


def test_conversational_follow_ups():
    emp_tok = get_token("employee@mindfulmetrics.com")
    headers = {"Authorization": f"Bearer {emp_tok}"}

    # Turn 1
    t1 = client.post("/api/ai/chat", json={"text": "What is my burnout risk?"}, headers=headers)
    assert t1.status_code == 200
    rep1 = t1.json()["reply"]

    # Turn 2: Follow-up "Why?"
    history = [
        {"role": "user", "text": "What is my burnout risk?"},
        {"role": "assistant", "text": rep1}
    ]
    t2 = client.post(
        "/api/ai/chat",
        json={"text": "Why?", "conversation_history": history},
        headers=headers
    )
    assert t2.status_code == 200
    rep2 = t2.json()["reply"]
    # Explains factors or reasons for the burnout risk
    assert any(w in rep2.lower() for w in ["risk", "factor", "workload", "indicator", "schedule", "because", "contribut"])

    # Turn 3: Follow-up "What should I do?"
    history.extend([
        {"role": "user", "text": "Why?"},
        {"role": "assistant", "text": rep2}
    ])
    t3 = client.post(
        "/api/ai/chat",
        json={"text": "What should I do?", "conversation_history": history},
        headers=headers
    )
    assert t3.status_code == 200
    rep3 = t3.json()["reply"]
    assert any(w in rep3.lower() for w in ["recommend", "break", "rest", "workload", "prioritize", "action", "recover"])


def test_rbac_peer_privacy_strictly_enforced():
    emp_tok = get_token("employee@mindfulmetrics.com")
    headers = {"Authorization": f"Bearer {emp_tok}"}

    # Employee asks about colleague Rahul Sharma
    res_peer = client.post(
        "/api/ai/chat",
        json={"text": "What is Rahul Sharma's burnout score?", "role": "employee"},
        headers=headers
    )
    assert res_peer.status_code == 200
    reply_peer = res_peer.json()["reply"]
    assert "privacy" in reply_peer.lower() or "confidential" in reply_peer.lower()


def test_manager_and_hr_intelligence():
    mgr_tok = get_token("manager@mindfulmetrics.com")
    mgr_headers = {"Authorization": f"Bearer {mgr_tok}"}

    # Manager asks about team members
    res_mgr = client.post(
        "/api/ai/chat",
        json={"text": "Which team member has the highest risk?", "role": "manager"},
        headers=mgr_headers
    )
    assert res_mgr.status_code == 200
    reply_mgr = res_mgr.json()["reply"]
    assert any(w in reply_mgr.lower() for w in ["team", "risk", "member", "workload", "indicator", "moderate", "high"])

    hr_tok = get_token("hr@mindfulmetrics.com")
    hr_headers = {"Authorization": f"Bearer {hr_tok}"}

    # HR asks about department
    res_hr = client.post(
        "/api/ai/chat",
        json={"text": "Which department has the highest burnout risk?", "role": "hr"},
        headers=hr_headers
    )
    assert res_hr.status_code == 200
    reply_hr = res_hr.json()["reply"]
    assert any(w in reply_hr.lower() for w in ["department", "engineering", "risk", "workforce", "indicator"])
