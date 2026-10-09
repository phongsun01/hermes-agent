param(
    [string]$SourceDir = "D:\Antigravity\Hermes",
    [string]$TargetDir = $(if ($env:HERMES_HOME) { $env:HERMES_HOME } else { "$env:USERPROFILE\.hermes" })
)

Write-Host ">>> Syncing: $SourceDir -> $TargetDir" -ForegroundColor Cyan

$folders = @("skills", "scripts", "plugins")

foreach ($f in $folders) {
    $src = Join-Path $SourceDir $f
    $dst = Join-Path $TargetDir $f
    if (Test-Path $src) {
        Write-Host "Syncing $f ..." -ForegroundColor Yellow
        & robocopy $src $dst /E /PURGE /XO /NFL /NDL /NJH /NJS
        if ($LASTEXITCODE -ge 8) {
            Write-Error "Robocopy $f failed with exit code $LASTEXITCODE"
        } else {
            Write-Host "Done $f." -ForegroundColor Green
        }
    }
}

Write-Host ">>> Sync completed successfully!" -ForegroundColor Cyan
