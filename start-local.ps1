$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$pythonExe = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) { throw 'Create .venv and install backend/requirements.txt first. See README.md.' }
Push-Location (Join-Path $projectRoot 'backend')
try {
    & $pythonExe -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) { throw 'Migration failed' }
    & $pythonExe seed.py
    if ($LASTEXITCODE -ne 0) { throw 'Seed failed' }
} finally { Pop-Location }
$backendProcess = Start-Process -FilePath $pythonExe -ArgumentList '-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000' -WorkingDirectory (Join-Path $projectRoot 'backend') -WindowStyle Hidden -PassThru
Write-Host "Backend started (PID $($backendProcess.Id)). Frontend: run npm run dev from frontend."
