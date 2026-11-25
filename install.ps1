param([switch]$Uninstall)
$ErrorActionPreference = "Stop"

$src = Join-Path $PSScriptRoot "plugin"
$dst = Join-Path $env:USERPROFILE ".gemini\config\plugins\media-traffic-guard"

if ($Uninstall) {
    if (Test-Path $dst) {
        Remove-Item -LiteralPath $dst -Recurse -Force
        Write-Host "[OK] Uninstalled media-traffic-guard from $dst" -ForegroundColor Yellow
    } else {
        Write-Host "[INFO] Plugin directory not found: $dst" -ForegroundColor Gray
    }
    exit 0
}

if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Warning "ffmpeg was not found in PATH. Install ffmpeg or set FFMPEG_PATH so video/image contact-sheet rewriting can run."
}

New-Item -ItemType Directory -Force -Path $dst, (Join-Path $dst "rules"), (Join-Path $dst "scripts") | Out-Null
Copy-Item -LiteralPath (Join-Path $src "plugin.json") -Destination (Join-Path $dst "plugin.json") -Force
Copy-Item -LiteralPath (Join-Path $src "rules\AGENTS.md") -Destination (Join-Path $dst "rules\AGENTS.md") -Force
Copy-Item -LiteralPath (Join-Path $src "scripts\media_guard.py") -Destination (Join-Path $dst "scripts\media_guard.py") -Force
Copy-Item -LiteralPath (Join-Path $src "hook-config.template.json") -Destination (Join-Path $dst "hooks.json") -Force

Write-Host "[OK] Installed media-traffic-guard to $dst" -ForegroundColor Green
Write-Host "     Open a new Antigravity conversation to activate. Uninstall anytime with: .\install.ps1 -Uninstall" -ForegroundColor Cyan
