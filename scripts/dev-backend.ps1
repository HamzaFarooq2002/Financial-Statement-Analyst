# Run FastAPI from the backend folder so `import app` always works.
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location (Join-Path $RepoRoot "backend")

if (Test-Path ".venv\Scripts\Activate.ps1") {
    .\.venv\Scripts\Activate.ps1
}

$py = $null
if (Get-Command python -ErrorAction SilentlyContinue) { $py = "python" }
elseif (Get-Command py -ErrorAction SilentlyContinue) { $py = "py" }
else {
    Write-Error "Python not found on PATH. Install Python or use the 'py' launcher."
    exit 1
}

Write-Host "Starting API at http://127.0.0.1:8000 (cwd: $(Get-Location); launcher=$py)" -ForegroundColor Green
& $py -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
