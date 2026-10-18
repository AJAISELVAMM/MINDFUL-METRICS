# MINDFUL METRICS — AI-Powered Employee Wellbeing & Burnout Intelligence Platform

> **Disclaimer:** Burnout-risk scores and analytics provided by Mindful Metrics are workplace wellness insights and organizational indicators designed for proactive workload balancing, **not** formal clinical or medical diagnoses.

---

## 1. Project Overview & Objectives

**Mindful Metrics** is a full-stack, enterprise-grade workplace intelligence platform engineered to monitor, predict, and mitigate workplace burnout and cognitive fatigue in real time. Combining physiological and organizational telemetry—such as attendance habits, overtime patterns, task workload fluctuations, sentiment-analyzed communications, and daily self-reported pulse surveys—Mindful Metrics enables employees, team managers, and HR administrators to identify early indicators of chronic workplace exhaustion and intervene proactively.

### Key Objectives
- **Early Warning System:** Predict personal burnout risk scores (0–100) using a 21-feature Random Forest classifier calibrated to three actionable tiers (LOW, MODERATE, HIGH).
- **Multi-Role Separation:** Role-Based Access Control (RBAC) ensuring strict data isolation between Employees, Managers, and HR Directors.
- **Actionable Workload Governance:** End-to-end task lifecycle tracking, including blocker declarations, HR unblock requests, and completion verification queues.
- **Attendance & Leave Governance:** Automated check-in/out windowing, late-arrival detection, short-session exception flagging, and leave/permission workflows.
- **Context-Aware AI Assistant:** Dual-engine AI conversational interface utilizing offline semantic intent parsing with seamless Google Gemini fallback.

---

## 2. Technology Stack

### Frontend
- **Framework:** React.js 19 (`react`, `react-dom`)
- **Bundler & Tooling:** Vite 8 (`vite`, `@vitejs/plugin-react`)
- **Styling:** Tailwind CSS 4 (`tailwindcss`, `@tailwindcss/vite`)
- **Routing:** React Router 7 (`react-router-dom`)
- **Visualizations:** Recharts 3 (`recharts`)
- **Icons:** Lucide React (`lucide-react`)
- **Code Quality:** Oxlint (`oxlint`)

### Backend & API
- **Framework:** Python 3.11+ / FastAPI (`fastapi`, `starlette`)
- **ASGI Server:** Uvicorn (`uvicorn[standard]`)
- **ORM & Data Layer:** SQLAlchemy 2 (`sqlalchemy`)
- **Database Driver:** `psycopg2-binary` (PostgreSQL) / `sqlite3`
- **Authentication:** HMAC-SHA256 JWT (`pyjwt`), Passlib / bcrypt (`passlib[bcrypt]`)
- **Validation:** Pydantic v2 (`pydantic`)
- **Testing:** Pytest & HTTPX (`pytest`, `httpx`)

### AI / Machine Learning
- **Classification Engine:** Scikit-Learn 1.6.1 (`scikit-learn==1.6.1`) Random Forest Classifier
- **Natural Language Processing:** Scikit-Learn TF-IDF Vectorizer + Logistic Regression Sentiment/Stress Classifier
- **Model Serialization:** Joblib (`joblib`)
- **Numerical Computing:** NumPy & Pandas (`numpy`, `pandas`)
- **Generative AI Fallback:** Google Generative AI SDK (`google-generativeai`)

### Infrastructure & Deployment
- **Database Hosting:** Supabase Managed PostgreSQL
- **Local Mobile / Remote Tunneling:** Cloudflare Quick Tunnels (`cloudflared`)

---

## 3. System Architecture & Workflows

```
┌─────────────────────────────────────────────────────────────┐
│                 React + Vite Frontend (Port 5173)           │
│   [Employee Portal]    [Manager Portal]    [HR Organization]│
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTPS / JSON REST
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 FastAPI Backend Server (Port 8000)          │
│   ├── Authentication & Role-Based Access Control (RBAC)     │
│   ├── Attendance & Schedule Engine (9:00 - 17:30 IST)       │
│   ├── Task Lifecycle & HR Verification Queue                │
│   ├── Daily & Pulse Survey Handlers                         │
│   ├── AI Chat Assistant & Intent Classifier                 │
│   └── Burnout Feature Engineering Pipeline (21 Features)    │
└──────────────┬───────────────────────────────┬──────────────┘
               │ SQLAlchemy                    │ Inference
               ▼                               ▼
┌──────────────────────────────┐ ┌────────────────────────────┐
│ PostgreSQL / Supabase DB     │ │ Scikit-Learn ML Artifacts  │
│ - 20 Relational Tables       │ │ - burnout_random_forest    │
│ - Full Audit Trails          │ │ - text_tfidf_logreg        │
│ - Zero Data Loss Guarantee   │ │ - semantic_encoder         │
└──────────────────────────────┘ └────────────────────────────┘
```

---

## 4. Repository Structure

```
workwell/
├── public/                     # Static brand assets and favicons
├── src/                        # React Frontend Source Code
│   ├── components/             # Reusable UI components & layouts
│   │   ├── common/             # Cards, tables, modals, badges, calendars
│   │   └── layout/             # AppShell, Navigation, Header, Sidebar
│   ├── pages/                  # Role-scoped view pages
│   │   ├── employee/           # Attendance, Work, Surveys, Recommendations
│   │   ├── manager/            # Team overview, Burnout analytics, Work process
│   │   └── hr/                 # Workforce analytics, Interventions, Tasks, Verification
│   ├── services/               # Centralized Axios/fetch API client (`api.js`)
│   └── App.jsx                 # Application entry route declarations
├── backend/                    # FastAPI Backend Source Code
│   ├── app/                    # Main application package
│   │   ├── main.py             # Route declarations & lifespan handlers
│   │   ├── config.py           # Environment config & cryptographic secret validator
│   │   ├── database.py         # SQLAlchemy engine & session dependency
│   │   ├── models.py           # 20 relational database models
│   │   ├── security.py         # Password hashing & JWT token management
│   │   ├── ml/                 # Model loader, feature assembler & matrix encoders
│   │   └── services/           # Core domain logic
│   │       ├── attendance_service.py   # Attendance rules & time calculations
│   │       ├── burnout_service.py      # Feature engineering & ML inference
│   │       ├── task_service.py         # Task CRUD, blocker & HR verification
│   │       ├── leave_service.py        # Leave balance & approval workflow
│   │       ├── survey_service.py       # Daily wellbeing & pulse submissions
│   │       ├── ai_chat_service.py      # Multi-turn chat & intent routing
│   │       └── notification_service.py # In-app notification dispatcher
│   ├── datasets/               # Verified synthetic training datasets
│   │   ├── burnout_training.csv        # 21-feature tabular benchmark dataset
│   │   └── communication_training.csv  # Sentiment & stress labeled phrases
│   ├── models/                 # Pre-trained ML model artifacts (.joblib, .json)
│   ├── scripts/                # Utility migration & database maintenance scripts
│   ├── tests/                  # Automated pytest test suites (140+ tests)
│   ├── training/               # Model training & synthetic data generation scripts
│   ├── requirements.txt        # Pinned Python dependencies
│   └── .env.example            # Sanitized backend environment template
├── .env.example                # Sanitized frontend environment template
├── CLOUDFLARE_MOBILE_TESTING.md# Cloudflare Quick Tunnel testing instructions
├── package.json                # Frontend NPM scripts & dependencies
├── vite.config.js              # Vite configuration & proxy definitions
└── README.md                   # Project documentation
```

---

## 5. Verified AI/ML Pipeline

The burnout risk engine utilizes 21 physiological and organizational features assembled in exact canonical order:

1. `stress_score` (Self-reported survey metric)
2. `workload_score` (Self-reported workload perception)
3. `work_life_balance_score` (Self-reported boundary balance)
4. `energy_score` (Self-reported energy level)
5. `mood_score` (Daily wellbeing baseline)
6. `job_satisfaction_score` (Role sentiment rating)
7. `working_hours` (Average daily logged hours)
8. `overtime_hours` (Hours worked beyond 17:30 IST)
9. `attendance_rate` (Working day presence percentage)
10. `leave_frequency` (Leave requests per time period)
11. `task_completion_rate` (Closed tasks / total assigned)
12. `deadline_pressure` (High-priority impending due dates)
13. `task_difficulty` (Weighted task complexity scale 1–5)
14. `workload_deviation` (Variance from team benchmark)
15. `working_hour_deviation` (Variance from standard 8-hour schedule)
16. `communication_sentiment` (NLP polarity of work updates)
17. `communication_stress_score` (Lexical stress keyword intensity)
18. `communication_negative_score` (Negative sentiment distribution)
19. `sem_mean` (TF-IDF semantic average vector)
20. `sem_std` (TF-IDF semantic dispersion)
21. `sem_norm` (Semantic magnitude norm)

### Risk Classification Tiers
- **LOW RISK (0–39):** Healthy workload and positive resilience metrics.
- **MODERATE RISK (40–69):** Approaching fatigue threshold; proactive rebalancing recommended.
- **HIGH RISK (70–100):** Severe burnout indicators; flagged in HR interventions queue.

---

## 6. Installation & Local Setup

### Prerequisites
- **Node.js:** v18.0.0 or higher
- **Python:** v3.11.0 to v3.11.9
- **Database:** PostgreSQL instance (or local SQLite fallback)

### Step 1: Clone Repository
```bash
git clone https://github.com/AJAISELVAMM/MINDFUL-METRICS.git
cd MINDFUL-METRICS
```

### Step 2: Configure Environment Variables
Copy the sanitized environment templates and configure local secrets:

**Frontend Configuration:**
```bash
cp .env.example .env.local
```

**Backend Configuration:**
```bash
cd backend
cp .env.example .env
```
Generate a cryptographically secure 32-byte JWT secret:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```
Paste this token as `JWT_SECRET` inside `backend/.env`.

### Step 3: Backend Setup & Execution
```bash
# In MINDFUL-METRICS/backend
python -m venv .venv

# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Linux/macOS:
# source .venv/bin/activate

pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Verify backend health: `http://localhost:8000/api/health`

### Step 4: Frontend Setup & Execution
Open a second terminal in the project root:
```bash
# In MINDFUL-METRICS/
npm install
npx vite --host 0.0.0.0 --port 5173
```
Visit the application in your browser: `http://localhost:5173`

---

## 7. Running Automated Tests

The backend test suite covers authentication, role authorization, attendance engine rules, task lifecycle state transitions, AI model contracts, and cross-employee data isolation:

```bash
cd backend

# Run all test suites
pytest

# Run specific domain test suites
pytest tests/test_attendance_logic_audit.py
pytest tests/test_task_lifecycle_master.py
pytest tests/test_employee_data_isolation_and_sync.py
pytest tests/test_ml.py
pytest tests/test_burnout_and_ai_master.py
```

Frontend linting & static analysis:
```bash
npm run lint
npm run build
```

---

## 8. Mobile & Remote Testing via Cloudflare Tunnel

To test on physical mobile devices or remote networks without exposing ports:
1. Start local backend (`port 8000`) and frontend (`port 5173`).
2. Run Cloudflare Quick Tunnels:
   ```bash
   cloudflared tunnel --protocol http2 --url http://localhost:8000
   cloudflared tunnel --protocol http2 --url http://localhost:5173
   ```
3. Update `.env.local` with the backend public URL:
   ```env
   VITE_API_BASE_URL=https://<your-backend-tunnel>.trycloudflare.com
   ```
4. Access the public frontend tunnel URL from your mobile device.

---

## 9. Security & Governance

- **Credential Protection:** Real `.env` files, `.env.local`, SQLite databases (`*.db`), and backup dumps are strictly excluded from version control via `.gitignore`.
- **JWT Cryptographic Enforcement:** Backend startup aborts in production mode if `JWT_SECRET` is shorter than 32 bytes (256 bits).
- **Row-Level Security & RBAC:** Employees cannot view peers' individual telemetry, burnout scores, or task updates. Managers can only assign tasks to direct reports. Sensitive HR intervention notes remain confidential.

---

## 10. License

Mindful Metrics is distributed under the [MIT License](LICENSE).
