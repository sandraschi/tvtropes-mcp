Param([switch]$Headless)

$svc = Get-Service -Name tvtropes-mcp -ErrorAction SilentlyContinue
if ($svc -and $svc.Status -eq 'Running') {
    Write-Host "tvtropes-mcp service is running -- starting frontend only" -ForegroundColor Cyan
    $WebRoot = Join-Path $PSScriptRoot "web_sota"
    Push-Location $WebRoot
    npm run dev
    Pop-Location
    exit
}

# Delegate to web_sota\start.ps1 which handles everything:
# winget prereqs, uv sync, npm install, port clearing, backend + frontend launch.
$webStart = Join-Path $PSScriptRoot "web_sota\start.ps1"
if (-not (Test-Path $webStart)) {
    Write-Host "ERROR: web_sota\start.ps1 not found." -ForegroundColor Red
    exit 1
}
& $webStart -Headless:$Headless
