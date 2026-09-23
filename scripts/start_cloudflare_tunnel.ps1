param(
    [ValidateSet("Quick", "Named")]
    [string]$Mode = "Quick",
    [string]$Origin = "http://127.0.0.1:5000",
    [string]$TunnelName = "vision-backend",
    [string]$ConfigPath = "cloudflare/config.yml"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot

if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) {
    throw "cloudflared가 설치되어 있지 않습니다. 'winget install --id Cloudflare.cloudflared'를 실행하세요."
}

$healthUrl = "$($Origin.TrimEnd('/'))/api/v1/health"
try {
    $health = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 10
    Write-Host "Backend health: $($health.status), model: $($health.modelType)" -ForegroundColor Green
}
catch {
    throw "Flask backend에 연결할 수 없습니다: $healthUrl`n먼저 backend/run.py를 실행하세요.`n$($_.Exception.Message)"
}

if ($Mode -eq "Quick") {
    Write-Host "Quick Tunnel을 시작합니다. 출력되는 trycloudflare.com URL을 사용하세요." -ForegroundColor Cyan
    & cloudflared tunnel --url $Origin
    exit $LASTEXITCODE
}

$resolvedConfig = [IO.Path]::GetFullPath((Join-Path $projectRoot $ConfigPath))
if (-not (Test-Path -LiteralPath $resolvedConfig)) {
    throw "Named Tunnel config가 없습니다: $resolvedConfig`ncloudflare/config.yml.example을 복사하고 UUID, credentials, hostname을 설정하세요."
}

Write-Host "Named Tunnel '$TunnelName'을 시작합니다." -ForegroundColor Cyan
& cloudflared tunnel --config $resolvedConfig run $TunnelName
exit $LASTEXITCODE
