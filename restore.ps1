# restore.ps1 — Hermes Agent Restore Script
# Usage: .\restore.ps1

param(
    [string]$BackupDir = "D:\Antigravity\Hermes-backup\2026-05-20_1225",
    [string]$HermesDir = "D:\Antigravity\Hermes"
)

Write-Host "📦 Hermes Agent Restore from $BackupDir" -ForegroundColor Cyan

# 1. Stop containers
Write-Host "`n⏸  Stopping containers..." -ForegroundColor Yellow
Push-Location $HermesDir
docker compose down

# 2. Extract userdata
Write-Host "`n💾 Restoring user data (.hermes)..." -ForegroundColor Yellow
if (Test-Path "$BackupDir\hermes-userdata.zip") {
    Expand-Archive -Path "$BackupDir\hermes-userdata.zip" -DestinationPath "$env:USERPROFILE\" -Force
    Write-Host "✅ User data restored to $env:USERPROFILE\.hermes" -ForegroundColor Green
} else {
    Write-Warning "Could not find hermes-userdata.zip in $BackupDir"
}

# 3. Restore docker-compose.yml
if (Test-Path "$BackupDir\docker-compose.yml") {
    Write-Host "`n📄 Restoring docker-compose.yml..." -ForegroundColor Yellow
    Copy-Item "$BackupDir\docker-compose.yml" "$HermesDir\docker-compose.yml" -Force
    Write-Host "✅ docker-compose.yml restored." -ForegroundColor Green
}

# 4. Restart containers
Write-Host "`n▶  Starting containers..." -ForegroundColor Yellow
docker compose up -d
Pop-Location

Write-Host "`n✨ Restore complete!" -ForegroundColor Green
