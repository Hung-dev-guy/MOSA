$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$envFile = Join-Path $projectRoot '.env.docker'

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw 'Không tìm thấy Docker. Hãy cài và mở Docker Desktop trước.'
}

docker info *> $null
if ($LASTEXITCODE -ne 0) {
    throw 'Docker Desktop chưa chạy. Hãy mở Docker Desktop rồi chạy lại script.'
}

if (-not (Test-Path -LiteralPath $envFile)) {
    $randomPart = [Guid]::NewGuid().ToString('N')
    $password = "Mosa!A1$randomPart"
    $settings = @(
        "MSSQL_SA_PASSWORD=$password"
        'DB_NAME=ECommerceMultimodalV1'
        'APP_PORT=5050'
        'SQL_PORT=14330'
    )
    [IO.File]::WriteAllLines(
        $envFile,
        $settings,
        [Text.UTF8Encoding]::new($false)
    )
    Write-Host 'Đã tạo cấu hình riêng tại .env.docker (file này không được đưa vào Git).'
}

$configuration = @{}
foreach ($line in Get-Content -LiteralPath $envFile) {
    if ($line -match '^([^#=]+)=(.*)$') {
        $configuration[$matches[1].Trim()] = $matches[2].Trim()
    }
}
$appPort = if ($configuration.ContainsKey('APP_PORT')) {
    $configuration['APP_PORT']
} else {
    '5050'
}

Push-Location $projectRoot
try {
    docker compose --env-file $envFile up --build --detach
    if ($LASTEXITCODE -ne 0) {
        throw 'Docker Compose khởi động không thành công.'
    }
    docker compose --env-file $envFile ps
    Write-Host ''
    Write-Host "MOSA đang chạy tại http://localhost:$appPort"
    Write-Host 'Dừng hệ thống bằng: .\stop-docker.ps1'
}
finally {
    Pop-Location
}
