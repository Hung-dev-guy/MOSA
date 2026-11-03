$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$envFile = Join-Path $projectRoot '.env.docker'

if (-not (Test-Path -LiteralPath $envFile)) {
    throw 'Không tìm thấy .env.docker. Hệ thống Docker có thể chưa được khởi tạo.'
}

Push-Location $projectRoot
try {
    docker compose --env-file $envFile down
}
finally {
    Pop-Location
}
