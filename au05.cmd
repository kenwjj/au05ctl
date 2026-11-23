@echo off
rem Launcher: au05 show | au05 apply | au05 set key1 "Ctrl+Alt+L"   (uses the local .venv)
"%~dp0.venv\Scripts\python.exe" "%~dp0au05ctl.py" %*
