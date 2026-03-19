$ErrorActionPreference = "Stop"

Write-Host "Validating environment..."
python scripts/check_setup.py

Write-Host "Starting webhook service in a new window..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\\..'; uvicorn webhook_app:app --reload --port 8000"

Write-Host "Starting Streamlit UI..."
Set-Location "$PSScriptRoot\.."
streamlit run app.py
