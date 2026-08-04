# Restauracion v2 - Build React + Copy to backend/static
Write-Host "Building React frontend..." -ForegroundColor Cyan
Set-Location "$PSScriptRoot\frontend"
npm run build
if ($LASTEXITCODE -ne 0) { Write-Host "Build FAILED" -ForegroundColor Red; exit 1 }
Write-Host "Copying to backend/static..." -ForegroundColor Cyan
Remove-Item "$PSScriptRoot\backend\static\*" -Recurse -Force -ErrorAction SilentlyContinue
Copy-Item "$PSScriptRoot\frontend\dist\*" "$PSScriptRoot\backend\static\" -Recurse
Write-Host "DONE! React build deployed to backend/static/" -ForegroundColor Green
