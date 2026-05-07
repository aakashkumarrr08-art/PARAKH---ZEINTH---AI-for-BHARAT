@echo off
set ROOT=%~dp0
cd /d "%ROOT%backend"
set MONGO_URI=mongodb://localhost:27017
set REDIS_URL=redis://localhost:6379/0
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
