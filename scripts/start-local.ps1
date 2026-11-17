# CodeSense AI Local Launcher (No Docker)
# Starts the Python AI service, Python backend, and React frontend in separate console windows.

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "   CodeSense AI Local Launcher (No Docker)   " -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $scriptDir) { $scriptDir = (Get-Location).Path }
$rootDir = (Get-Item $scriptDir).Parent.FullName
if (-not (Test-Path "$rootDir\ai-service")) {
    $rootDir = (Get-Location).Path
}

Write-Host "Root Directory: $rootDir" -ForegroundColor DarkGray

Write-Host "[1/3] Launching AI Service (FastAPI on :8000)..." -ForegroundColor Yellow
Start-Process powershell -WorkingDirectory "$rootDir\ai-service" -ArgumentList "-NoExit", "-Command", "`$Host.UI.RawUI.WindowTitle='CodeSense AI Service (:8000)'; python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

Write-Host "[2/3] Launching Backend API (FastAPI on :8050)..." -ForegroundColor Yellow
Start-Process powershell -WorkingDirectory "$rootDir\backend" -ArgumentList "-NoExit", "-Command", "`$Host.UI.RawUI.WindowTitle='CodeSense Backend API (:8050)'; python -m uvicorn app.main:app --host 0.0.0.0 --port 8050 --reload"

Write-Host "[3/3] Launching Frontend (Vite + React on :5173)..." -ForegroundColor Yellow
Start-Process powershell -WorkingDirectory "$rootDir\frontend" -ArgumentList "-NoExit", "-Command", "`$Host.UI.RawUI.WindowTitle='CodeSense Frontend (:5173)'; npm.cmd run dev"

Write-Host "=============================================" -ForegroundColor Green
Write-Host "All services have been launched in separate console windows." -ForegroundColor Green
Write-Host "- Frontend: http://localhost:5173" -ForegroundColor Green
Write-Host "- Backend API: http://localhost:8050/api/health" -ForegroundColor Green
Write-Host "- AI Service: http://localhost:8000/health" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
