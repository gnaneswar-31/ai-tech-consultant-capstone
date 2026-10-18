
$ErrorActionPreference = "Stop"

$root = "D:\AI Tech Consultant\ai_tech_consultant_capstone"
$python = "D:\AI Tech Consultant\.venv\Scripts\python.exe"

$task1 = Join-Path $root "task1_knowledge_brain"
$task2 = Join-Path $root "task2_inbox_agent"
$task3 = Join-Path $root "task3_meeting_scope"

Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "Set-Location '$task1'; & '$python' -m uvicorn app.main:app --reload --port 8000"
)

Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "Set-Location '$task2'; npm.cmd run dev"
)

Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "Set-Location '$task3'; & '$python' -m uvicorn app.main:app --reload --port 8001"
)

Write-Host "Startup commands launched. Check each new PowerShell window for errors."
