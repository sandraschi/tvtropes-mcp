# Fleet Biome gate for web frontends.
# Runs `npx biome ci <src>` inside web_sota/ (or webapp/, webapp/frontend/, web/).
# Exit nonzero on lint errors so the commit fails CLOSED, not silent.
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$candidates = @("web_sota", "webapp", "web", "frontend")
$webDir = $null
foreach ($c in $candidates) {
    $p = Join-Path $repoRoot $c
    if (Test-Path (Join-Path $p "package.json")) { $webDir = $p; break }
}
if ($null -eq $webDir) { exit 0 }

$srcDir = Join-Path $webDir "src"
if (-not (Test-Path $srcDir)) { exit 0 }

$localBiome = Join-Path $webDir "node_modules/.bin/biome.cmd"
$bunx = Join-Path $env:USERPROFILE ".bun/bin/bunx.exe"
$npx = "C:/Program Files/nodejs/npx.cmd"

Push-Location $webDir
try {
    if (Test-Path $localBiome) {
        & $localBiome ci src/
    } elseif (Test-Path $bunx) {
        & $bunx --package @biomejs/biome biome ci src/
    } elseif (Test-Path $npx) {
        & $npx --no-install biome ci src/
    } else {
        Write-Warning "pre-commit-biome: no biome executable found (node_modules/.bin, bunx, npx all missing)"
        exit 1
    }
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
