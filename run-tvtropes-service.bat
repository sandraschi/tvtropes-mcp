@echo off
cd /d D:\Dev\repos\tvtropes-mcp
set PATH=C:\Users\sandr\.local\bin;%PATH%
set UV_PROJECT_ENVIRONMENT=D:\Dev\repos\tvtropes-mcp\.venv
C:\Users\sandr\.local\bin\uv.exe run --directory D:\Dev\repos\tvtropes-mcp python run_server.py
