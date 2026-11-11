$ErrorActionPreference='Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path '.venv\Scripts\python.exe')) { python -m venv .venv }
& .\.venv\Scripts\python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed' }
& .\.venv\Scripts\python scripts/prepare_text_search.py
if ($LASTEXITCODE -ne 0) { Write-Warning 'Semantic model unavailable; keyword search remains available. Retry scripts/prepare_text_search.py later.' }
if (-not (Test-Path 'frontend\node_modules')) {
    & npm ci --prefix frontend
    if ($LASTEXITCODE -ne 0) { throw 'Node dependency installation failed' }
}
& npm --prefix frontend run build
if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed' }
& .\.venv\Scripts\python run.py
