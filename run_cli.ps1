Write-Host 'BuddAI CLI Launcher' -ForegroundColor Cyan

# Ensure execution happens in the script's directory
Set-Location $PSScriptRoot

# 1. Check Ollama Status
if (Get-Command ollama -ErrorAction SilentlyContinue) {
    if (-not (Get-Process ollama* -ErrorAction SilentlyContinue)) {
        Write-Host 'Ollama is not running. Starting...' -ForegroundColor Yellow
        Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden
        Start-Sleep -Seconds 5
    } else {
        Write-Host 'Ollama is running.' -ForegroundColor Green
    }
}

# 2. Check Models
if (Get-Command ollama -ErrorAction SilentlyContinue) {
    Write-Host 'Checking AI models...' -ForegroundColor Green
    $models = ollama list | Out-String
    $required = @('qwen2.5-coder:1.5b', 'qwen2.5-coder:3b')
    foreach ($model in $required) {
        if ($models -notmatch [regex]::Escape($model)) {
            Write-Host "Model '$model' missing. Pulling (this may take a while)..." -ForegroundColor Yellow
            ollama pull $model
        }
    }
}

# 3. Create Virtual Environment if missing
if (-not (Test-Path 'venv')) {
    Write-Host 'Creating Python virtual environment...' -ForegroundColor Green
    python -m venv venv
}

# 4. Install Dependencies
Write-Host 'Checking dependencies...' -ForegroundColor Green
./venv/Scripts/python.exe -m pip install -r requirements.txt > $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Dependency installation failed." -ForegroundColor Red
    exit
}

# 5. Run CLI
Write-Host 'Starting BuddAI CLI...' -ForegroundColor Cyan
./venv/Scripts/python.exe main.py