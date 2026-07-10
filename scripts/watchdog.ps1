param(
    [string]$Name = "tvtropes-scraper",
    [string]$Cwd = "",
    [switch]$Install,
    [switch]$Remove
)

$ErrorActionPreference = "Stop"
$MyRoot = if ($Cwd) { Resolve-Path $Cwd } else { Split-Path -Parent (Split-Path -Parent $PSCommandPath) }
$DataDir = Join-Path $MyRoot "data"
$PidFile = Join-Path $DataDir "$Name.pid"
$LogFile = Join-Path $DataDir "$Name-watchdog.log"

function Log { param([string]$Msg) $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"; "$ts [$Name-watchdog] $Msg" | Out-File $LogFile -Append -Encoding utf8 }

if ($Install) {
    $taskName = "Fleet-$Name"
    $arg = "-NoProfile -File `"$PSCommandPath`" -Cwd `"$MyRoot`""
    $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arg
    $trigger = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Minutes 5) -RepetitionDuration (New-TimeSpan -Days 365) -At (Get-Date) -Once
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -User (whoami) -RunLevel Limited -Force
    Write-Host "Installed Scheduled Task '$taskName' (every 5 min)"
    return
}

if ($Remove) {
    Unregister-ScheduledTask -TaskName "Fleet-$Name" -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed Scheduled Task 'Fleet-$Name'"
    return
}

Log "Liveness check starting"

$childPid = $null
if (Test-Path $PidFile) {
    try {
        $childPid = (Get-Content $PidFile -Raw).Trim()
        $p = Get-Process -Id $childPid -ErrorAction SilentlyContinue
        if (-not $p) { $childPid = $null }
    } catch { $childPid = $null }
}

if ($childPid) {
    Log "Process alive (PID $childPid)"
    try {
        $r = & "uv" "run" "python" "-c" "import sys; sys.path.insert(0,'src'); sys.path.insert(0,'scraper'); from tvtropes_mcp.db import scraper_status, ensure_db; ensure_db('data/tvtropes.db'); s = scraper_status('data/tvtropes.db'); print(s['crawl']['pages_visited'] or 0)" 2>&1
        Log "Progress: $([int]($r -replace '\D','')) pages visited"
    } catch { Log "Progress check failed: $_" }
    exit 0
}

Log "Process dead - restarting"
$oldPids = Get-Process -Name "python*" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match $Name.Replace("-",".") }
foreach ($p in $oldPids) {
    try { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue } catch {}
    Start-Sleep 1
}

$proc = Start-Process -FilePath "uv" -ArgumentList "run","python","-m","tvtropes_mcp","--scrape" -WorkingDirectory $MyRoot -NoNewWindow -PassThru
$proc.Id | Out-File $PidFile -Encoding utf8 -Force
Log ("Started new PID " + $proc.Id)
