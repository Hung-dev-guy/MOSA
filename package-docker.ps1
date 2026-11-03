$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$outputDirectory = Join-Path $projectRoot 'output'
$archivePath = Join-Path $outputDirectory 'MOSA-Stationery-Docker.zip'
$tempRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
$stagingRoot = Join-Path $tempRoot ("mosa-package-" + [Guid]::NewGuid().ToString('N'))
$stagingProject = Join-Path $stagingRoot 'multimodal-store'

$resolvedStaging = [IO.Path]::GetFullPath($stagingRoot)
if (-not $resolvedStaging.StartsWith($tempRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Thư mục đóng gói tạm không nằm trong thư mục tạm của hệ thống.'
}

$files = @(
    '.dockerignore',
    '.env.docker.example',
    '.env.example',
    '.gitignore',
    'app.py',
    'Dockerfile',
    'docker-compose.yml',
    'package-docker.ps1',
    'README.md',
    'requirements.txt',
    'requirements-docker.txt',
    'run.ps1',
    'start-docker.ps1',
    'stop-docker.ps1'
)
$directories = @('database', 'src', 'static', 'templates', 'tools')

try {
    New-Item -ItemType Directory -Path $stagingProject -Force | Out-Null
    foreach ($file in $files) {
        Copy-Item -LiteralPath (Join-Path $projectRoot $file) -Destination $stagingProject
    }
    foreach ($directory in $directories) {
        Copy-Item -LiteralPath (Join-Path $projectRoot $directory) -Destination $stagingProject -Recurse
    }

    Get-ChildItem -LiteralPath $stagingProject -Directory -Recurse -Filter '__pycache__' |
        Remove-Item -Recurse -Force

    New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null
    if (Test-Path -LiteralPath $archivePath) {
        Remove-Item -LiteralPath $archivePath -Force
    }
    Compress-Archive -LiteralPath $stagingProject -DestinationPath $archivePath -CompressionLevel Optimal
    Write-Host "Đã tạo gói gửi bạn bè: $archivePath"
}
finally {
    if (Test-Path -LiteralPath $resolvedStaging) {
        Remove-Item -LiteralPath $resolvedStaging -Recurse -Force
    }
}
