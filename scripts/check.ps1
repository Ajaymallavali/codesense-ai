Write-Host "Checking frontend TypeScript build..."
Push-Location frontend
npm.cmd run build
Write-Host "Running frontend Vitest test suite..."
npm.cmd test
Pop-Location

Write-Host "Checking backend and ai-service Python syntax..."
python -m compileall backend/app ai-service/app

Write-Host "Running comprehensive Pytest test suite..."
python -m pytest

