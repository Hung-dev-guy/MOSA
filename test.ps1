$ErrorActionPreference='Stop'
Set-Location -LiteralPath $PSScriptRoot
& npm --prefix frontend run build
if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed' }
& .\.venv\Scripts\python -m pytest -q --junitxml=docs/pytest-results.xml
if ($LASTEXITCODE -ne 0) { throw 'Backend tests failed' }
& npm --prefix frontend run test:e2e
if ($LASTEXITCODE -ne 0) { throw 'Browser tests failed' }
Write-Host 'All checks passed. Reports are in docs/.'
