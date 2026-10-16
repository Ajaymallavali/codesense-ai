# CodeSense AI Local Launcher (No Docker)
# Starts the Python AI service, Python backend, and React frontend in separate PowerShell windows.

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "   CodeSense AI Local Launcher (No Docker)   " -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

$pythonCmd = "python"
if (Test-Path "backend\.venv\Scripts\python.exe") {
    $backendPython = ".\.venv\Scripts\python"
} else {
    $backendPython = "python"
}

if (Test-Path "ai-service\.venv\Scripts\python.exe") {
    $aiPython = ".\.venv\Scripts\python"
} else {
    $aiPython = "python"
}

Write-Host "[1/3] Launching AI Service (FastAPI on :8000)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$Host.UI.RawUI.WindowTitle='CodeSense AI Service (:8000)'; cd ai-service; $aiPython -m uvicorn app.main:app --port 8000 --reload"

Write-Host "[2/3] Launching Backend API (FastAPI on :8050)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$Host.UI.RawUI.WindowTitle='CodeSense Backend API (:8050)'; cd backend; $backendPython -m uvicorn app.main:app --port 8050 --reload"

Write-Host "[3/3] Launching Frontend (Vite + React on :5173)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$Host.UI.RawUI.WindowTitle='CodeSense Frontend (:5173)'; cd frontend; npm.cmd run dev"

Write-Host "=============================================" -ForegroundColor Green
Write-Host "All services have been launched in separate console windows." -ForegroundColor Green
Write-Host "- Frontend: http://localhost:5173" -ForegroundColor Green
Write-Host "- Backend API: http://localhost:8050/api/health" -ForegroundColor Green
Write-Host "- AI Service: http://localhost:8000/health" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
