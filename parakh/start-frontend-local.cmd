@echo off
set ROOT=%~dp0
cd /d "%ROOT%frontend"
set NEXT_PUBLIC_API_BASE=http://localhost:8000/api
cmd /c npm.cmd run dev
