@echo off
rem Starts the app and opens it. First time: see README.
cd /d %~dp0
start http://127.0.0.1:5895
.venv\Scripts\python.exe app.py
