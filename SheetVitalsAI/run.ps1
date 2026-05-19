# Start SheetVitals AI
Write-Host "🚀 Starting SheetVitals AI..." -ForegroundColor Cyan

# Start Backend
Write-Host "📦 Starting Backend on port 8001..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend; pip install -r requirements.txt; python main.py"

# Start Frontend
Write-Host "🌐 Starting Frontend on port 8002..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; python -m http.server 8002"

Write-Host "✅ Done!" -ForegroundColor Green
Write-Host "Open: http://localhost:8002"
