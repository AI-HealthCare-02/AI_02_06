# ============================================================
# 환경 전환 스크립트 (Windows PowerShell)
# 사용법: .\scripts\switch-env.ps1 local|dev|prod
# ============================================================

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("local", "dev", "prod")]
    [string]$Environment
)

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$EnvFile = Join-Path $ProjectRoot ".env"

# 소스 파일 결정 (local/dev는 같은 파일 사용)
if ($Environment -eq "prod") {
    $SourceFile = Join-Path $ProjectRoot "envs\.prod.env"
} else {
    $SourceFile = Join-Path $ProjectRoot "envs\.local.env"
}

# 소스 파일 확인
if (-not (Test-Path $SourceFile)) {
    Write-Host "[ERROR] Source file not found: $SourceFile" -ForegroundColor Red
    exit 1
}

# 기존 .env 삭제 (심볼릭 링크 또는 파일)
if (Test-Path $EnvFile) {
    Remove-Item $EnvFile -Force
}

# 파일 복사 (심볼릭 링크 대신 복사 - ENV 값 수정 필요)
Copy-Item $SourceFile $EnvFile

# ENV 값 수정 (local/dev 구분) - 멀티라인 모드로 정규식 적용
$content = Get-Content $EnvFile -Raw
$content = $content -replace "(?m)^ENV=.*$", "ENV=$Environment"
$content = $content -replace "(?m)^NEXT_PUBLIC_ENV=.*$", "NEXT_PUBLIC_ENV=$Environment"
Set-Content $EnvFile $content -NoNewline

Write-Host "[OK] Switched to '$Environment' environment" -ForegroundColor Green
Write-Host "     Source: envs\.$(if ($Environment -eq 'prod') {'prod'} else {'local'}).env" -ForegroundColor Cyan
Write-Host ""
Write-Host "Current ENV: $Environment" -ForegroundColor Magenta
Write-Host "NEXT_PUBLIC_ENV: $Environment" -ForegroundColor Magenta
