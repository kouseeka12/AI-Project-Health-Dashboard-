$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $command = Get-Command python -ErrorAction Stop
    $python = $command.Source
}
Write-Host "Open http://127.0.0.1:8000 after the server starts."
Write-Host "MongoDB must also be running. See scripts\start_mongodb.ps1."
& $python -m uvicorn src.web_app:app --host 127.0.0.1 --port 8000
if ($LASTEXITCODE -ne 0) { throw "Dashboard exited with code $LASTEXITCODE. Check the output above." }
