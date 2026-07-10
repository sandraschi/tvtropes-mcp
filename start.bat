@echo off
cd /d "%~dp0"

:: Restart via NSSM if service exists
C:\Windows\System32\sc.exe query tvtropes-mcp >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo tvtropes-mcp service found -- restarting via NSSM
    "C:\Program Files\Jellyfin\Server\nssm.exe" restart tvtropes-mcp
    echo Done.
    exit /b 0
)

:: Fallback: use pwsh
pwsh.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
