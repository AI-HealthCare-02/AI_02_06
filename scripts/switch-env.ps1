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
$SourceFile = Join-Path $ProjectRoot "envs\.$Environment.env"

# dev 환경은 local과 동일한 파일 사용 (ENV 값만 다름)
if ($Environment -eq "dev") {
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

# 심볼릭 링크 생성 (관리자 권한 필요할 수 있음)
try {
    New-Item -ItemType SymbolicLink -Path $EnvFile -Target $SourceFile -ErrorAction Stop | Out-Null
    Write-Host "[OK] Switched to '$Environment' environment" -ForegroundColor Green
    Write-Host "     .env -> envs\.$Environment.env" -ForegroundColor Cyan
} catch {
    # 심볼릭 링크 실패 시 복사로 대체
    Write-Host "[WARN] Symlink failed, copying file instead..." -ForegroundColor Yellow
    Copy-Item $SourceFile $EnvFile
    Write-Host "[OK] Copied '$Environment' environment to .env" -ForegroundColor Green
}

# 현재 환경 표시
$CurrentEnv = Get-Content $EnvFile | Select-String "^ENV=" | ForEach-Object { $_.ToString().Split("=")[1] }
Write-Host ""
Write-Host "Current ENV: $CurrentEnv" -ForegroundColor Magenta
