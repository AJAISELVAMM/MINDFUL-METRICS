@echo off
cd /d d:\mindful\workwell
start "Frontend" cmd /k "npm run dev"
cd backend
start "Backend" cmd /k "d:\mindful\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
