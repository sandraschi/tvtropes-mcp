@echo off
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Please run as Administrator
    pause
    exit /b 1
)

set NSSM="C:\Program Files\Jellyfin\Server\nssm.exe"
set DIR=%~dp0

%NSSM% stop tvtropes-mcp 2>nul
%NSSM% remove tvtropes-mcp confirm 2>nul

%NSSM% install tvtropes-mcp "%DIR%run-tvtropes-service.bat"
%NSSM% set tvtropes-mcp AppDirectory "%DIR%"
%NSSM% set tvtropes-mcp AppStdout "%DIR%\logs\service-stdout.log"
%NSSM% set tvtropes-mcp AppStderr "%DIR%logs\service-stderr.log"
%NSSM% set tvtropes-mcp Start SERVICE_AUTO_START
%NSSM% set tvtropes-mcp AppRotateFiles 1
%NSSM% set tvtropes-mcp AppRotateSeconds 86400
%NSSM% set tvtropes-mcp AppRotateBytes 10485760

%NSSM% start tvtropes-mcp
echo tvtropes-mcp service installed and started
