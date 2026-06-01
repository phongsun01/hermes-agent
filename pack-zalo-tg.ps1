# pack-zalo-tg.ps1
# Clean pack zalo-tg bridge for migration to another machine
# Exclude node_modules, dist, and .git to optimize file size

$source = "D:\Antigravity\Hermes\zalo-tg"
$destination = "D:\Antigravity\Hermes-backup\zalo-tg-migration"
$zipPath = "D:\Antigravity\Hermes-backup\zalo-tg-migration.zip"

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "  START PACKAGING ZALO-TG MIGRATION PACKAGE   " -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "Source directory: $source"
Write-Host "Temp directory: $destination"
Write-Host "Output zip file: $zipPath"

# 1. Clean old temp directory if exists
if (Test-Path $destination) {
    Write-Host "Cleaning old temporary directory..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force $destination
}
New-Item -ItemType Directory -Path $destination -Force | Out-Null

# 2. Copy file structure excluding node_modules, dist, .git
Write-Host "Copying config files, source code, and sessions..." -ForegroundColor Yellow
Get-ChildItem -Path $source -Recurse | Where-Object {
    $_.FullName -notlike "*node_modules*" -and $_.FullName -notlike "*dist*" -and $_.FullName -notlike "*.git*"
} | ForEach-Object {
    $targetPath = $_.FullName.Replace($source, $destination)
    if ($_.PSIsContainer) {
        if (-not (Test-Path $targetPath)) {
            New-Item -ItemType Directory -Path $targetPath -Force | Out-Null
        }
    } else {
        $parentDir = Split-Path $targetPath
        if (-not (Test-Path $parentDir)) {
            New-Item -ItemType Directory -Path $parentDir -Force | Out-Null
        }
        Copy-Item -Path $_.FullName -Destination $targetPath -Force
    }
}

# 3. Compress to zip file
Write-Host "Compressing files into migration zip package..." -ForegroundColor Yellow
if (Test-Path $zipPath) {
    Remove-Item -Force $zipPath
}
Compress-Archive -Path "$destination\*" -DestinationPath $zipPath -Force

# 4. Clean up temp directory
Write-Host "Cleaning up temporary resources..." -ForegroundColor Yellow
Remove-Item -Recurse -Force $destination

Write-Host "==============================================" -ForegroundColor Green
Write-Host "  PACKAGING SUCCESSFUL!                      " -ForegroundColor Green
Write-Host "  Migration package is saved at: $zipPath    " -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Green
