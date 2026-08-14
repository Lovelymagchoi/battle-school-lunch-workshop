#!/usr/bin/env pwsh
# 급식배틀 앱(백엔드 + 프론트엔드)을 한 번에 실행하는 스크립트 (Windows PowerShell / PowerShell Core)
# 사용법: $env:NEIS_API_KEY="발급받은키"; pwsh ./run.ps1

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$apiDir = Join-Path $repoRoot "src/api"
$webDir = Join-Path $repoRoot "src/web"

if (-not (Test-Path $apiDir)) {
    Write-Error "백엔드 디렉터리를 찾을 수 없습니다: $apiDir"
    exit 1
}
if (-not (Test-Path $webDir)) {
    Write-Error "프론트엔드 디렉터리를 찾을 수 없습니다: $webDir"
    exit 1
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Error "uv를 찾을 수 없습니다. https://docs.astral.sh/uv/ 에서 먼저 설치해 주세요."
    exit 1
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Error "npm을 찾을 수 없습니다. Node.js를 먼저 설치해 주세요. (https://nodejs.org)"
    exit 1
}

$envFile = Join-Path $apiDir ".env"
if (-not $env:NEIS_API_KEY -and -not (Test-Path $envFile)) {
    Write-Warning "$envFile 파일이 없습니다. .env.example을 복사한 후 NEIS_API_KEY를 설정하세요."
    Write-Warning "NEIS_API_KEY 없이는 백엔드가 NEIS API를 호출할 수 없습니다."
}

Write-Host "백엔드 의존성을 확인합니다..." -ForegroundColor Cyan
Push-Location $apiDir
try {
    uv sync
}
finally {
    Pop-Location
}

if (-not (Test-Path (Join-Path $webDir "node_modules"))) {
    Write-Host "프론트엔드 의존성을 설치합니다..." -ForegroundColor Cyan
    Push-Location $webDir
    try {
        npm install
    }
    finally {
        Pop-Location
    }
}

Write-Host "백엔드 서버를 시작합니다 (http://localhost:8000)..." -ForegroundColor Green
$apiJob = Start-Job -ScriptBlock {
    param($dir)
    Set-Location $dir
    uv run uvicorn app.main:app --reload --port 8000
} -ArgumentList $apiDir

try {
    Write-Host "프론트엔드 개발 서버를 시작합니다 (http://localhost:5173)..." -ForegroundColor Green
    Push-Location $webDir
    try {
        npm run dev
    }
    finally {
        Pop-Location
    }
}
finally {
    Write-Host "백엔드 서버를 종료합니다..." -ForegroundColor Yellow
    Stop-Job $apiJob -ErrorAction SilentlyContinue | Out-Null
    Receive-Job $apiJob -ErrorAction SilentlyContinue | Out-Null
    Remove-Job $apiJob -ErrorAction SilentlyContinue | Out-Null
}

