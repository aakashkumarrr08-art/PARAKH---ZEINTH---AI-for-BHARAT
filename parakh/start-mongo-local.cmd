@echo off
set ROOT=%~dp0
"%ROOT%local-runtime\mongodb\mongodb-win32-x86_64-windows-8.0.18\bin\mongod.exe" --dbpath "%ROOT%local-runtime\data\db"
