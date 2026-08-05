@echo off
cd /d D:\Dev\repos\tvtropes-mcp
set PATH=C:\Users\sandr\.local\bin;%PATH%
"%~dp0.venv\Scripts\python.exe" run_server.py
